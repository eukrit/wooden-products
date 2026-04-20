"""POST /order/<id>/submit — the end-to-end order submission flow.

Steps:
  1. Validate (server-side reuses orders._validate_submit).
  2. Assign order number SO-WD-{year}-{seq:04d} via Firestore transaction.
  3. Snapshot FX onto each line item (reconstruction later).
  4. Create Xero draft invoice (lookup/create Contact, ensure Items).
  5. Post Slack Block Kit message to #orders-wood-products.
  6. Finalize: status='submitted', submitted_at=now, audit events.

Failure mode: if Xero or Slack fails, the order stays draft, the endpoint
returns HTTP 202 with {ok:true, degraded:true, failure:"..."}. Admin can
retry from the detail view.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from flask import g, jsonify, request, url_for

from . import bp, config as cfg, fx, slack_orders, xero_client
from .auth import require_auth
from . import firestore_client as fs
from . import orders as orders_mod

log = logging.getLogger("order_portal.submit")


# ---------- Order number atomic counter ----------

def _next_order_number() -> str:
    """Atomic increment of counters/order_number; format SO-WD-YYYY-NNNN."""
    db = fs.get_db()
    counter_ref = db.collection("counters").document("order_number")
    cfg_num = cfg.order_number()
    target_year = cfg_num["year"]

    @_transactional(db)
    def _tx(tx):
        snap = counter_ref.get(transaction=tx)
        data = snap.to_dict() if snap.exists else None
        if not data or data.get("year") != target_year:
            data = {"year": target_year, "next": 1}
        seq = int(data["next"])
        data["next"] = seq + 1
        tx.set(counter_ref, data)
        return seq

    seq = _tx()
    return cfg_num["format"].format(prefix=cfg_num["prefix"], year=target_year, seq=seq)


def _transactional(db):
    """Tiny wrapper around google.cloud.firestore.transactional decorator."""
    from google.cloud import firestore  # lazy
    def decorator(fn):
        @firestore.transactional
        def wrapped(tx):
            return fn(tx)
        def caller():
            tx = db.transaction()
            return wrapped(tx)
        return caller
    return decorator


# ---------- Xero Contact fallback ----------

def _get_or_create_fallback_contact() -> str:
    """Look up (or create once) the 'Wood Product Customer' fallback, cache ID in Firestore."""
    db = fs.get_db()
    cache_ref = db.collection("counters").document("xero_fallback_contact_id")
    snap = cache_ref.get()
    if snap.exists:
        val = (snap.to_dict() or {}).get("value")
        if val:
            return val
    xcfg = cfg.xero()
    contact_id = xero_client.upsert_contact(
        email=xcfg["fallback_contact_email"],
        name=xcfg["fallback_contact_name"],
        company=xcfg["fallback_contact_name"],
    )
    cache_ref.set({"value": contact_id, "cached_at": datetime.now(timezone.utc)})
    log.info("Cached Xero fallback ContactID=%s", contact_id)
    return contact_id


def _resolve_xero_contact(customer: dict[str, Any]) -> tuple[str, bool]:
    """Find Xero Contact by email, fall back to 'Wood Product Customer'.

    Returns (contact_id, used_fallback).
    """
    email = (customer.get("email") or "").strip()
    if email:
        try:
            cid = xero_client.upsert_contact(
                email=email,
                name=customer.get("name") or email,
                company=customer.get("company") or None,
                phone=customer.get("phone") or None,
            )
            return cid, False
        except Exception as exc:
            log.warning("Xero contact upsert failed for %s (%s); using fallback", email, exc)

    return _get_or_create_fallback_contact(), True


# ---------- Main submit ----------

@bp.route("/order/<order_id>/submit", methods=["POST"], endpoint="order_submit")
@require_auth
def order_submit(order_id: str):
    order = orders_mod._load_order(order_id)
    if not order:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if not orders_mod._can_access(order, g.user):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    if order.get("status") != "draft":
        return jsonify({
            "ok": False, "error": "already_submitted",
            "detail": f"status={order.get('status')}",
        }), 409

    # 1. Validate
    ok, errors = orders_mod._validate_submit(order, g.user["role"])
    if not ok:
        return jsonify({"ok": False, "error": "invalid", "errors": errors}), 400

    db = fs.get_db()
    ref = orders_mod._ref(order_id)

    # 2. Order number
    try:
        order_number = _next_order_number()
    except Exception as exc:
        log.exception("Failed to allocate order number")
        return jsonify({"ok": False, "error": "order_number_failed", "detail": str(exc)}), 500

    # 3. FX snapshot for each line
    fx_rate, fx_snapshot = fx.get_thb_per_usd()
    lines: list[dict[str, Any]] = []
    for ln in order.get("line_items") or []:
        ln_out = dict(ln)
        ln_out["fx_snapshot"] = fx_snapshot
        lines.append(ln_out)

    now = datetime.now(timezone.utc)
    base_url = request.url_root.rstrip("/")
    xcfg = cfg.xero()

    # 4. Xero draft invoice
    xero_draft_id: str | None = None
    xero_error: str | None = None
    used_fallback = False

    if xero_client.is_configured():
        try:
            contact_id, used_fallback = _resolve_xero_contact(order.get("customer", {}) or {})
            # Ensure every Item exists (auto-create any missing ones)
            for ln in lines:
                sku = ln.get("sku")
                name = ln.get("name") or sku
                if sku:
                    try:
                        xero_client.ensure_item(sku, name)
                    except Exception as exc:
                        log.warning("ensure_item(%s) failed (%s) — proceeding; Xero may still accept", sku, exc)
            # Build invoice line items
            xero_items = [
                {
                    "sku": ln["sku"],
                    "name": ln["name"],
                    "quantity": ln.get("quantity_m", 0),
                    "unit_price_thb": ln.get("unit_price_thb", 0),
                }
                for ln in lines
                if ln.get("sku") and ln.get("quantity_m")
            ]
            xero_draft_id = xero_client.create_invoice(
                contact_id=contact_id,
                reference=order_number,
                items=xero_items,
                tracking_category=xcfg.get("tracking_category"),
                tracking_option=None,  # Tracking values must exist in Xero — skip option until configured
                status=xcfg["draft_status"],
                currency_code="THB",
            )
        except Exception as exc:
            xero_error = str(exc)[:300]
            log.exception("Xero invoice creation failed for order %s", order_number)
    else:
        xero_error = "xero_not_configured"

    # 5. Slack post
    slack_ts: str | None = None
    slack_error: str | None = None
    staged_order = dict(order, _id=order_id, order_number=order_number, line_items=lines)
    slack_ok, ts, serr = slack_orders.post_new_order(
        staged_order,
        submitter_email=g.user.get("email") or "",
        portal_base_url=base_url,
        xero_draft_id=xero_draft_id,
    )
    if slack_ok:
        slack_ts = ts
    else:
        slack_error = serr
        log.warning("Slack post failed for order %s: %s", order_number, serr)

    # 6. Write state
    degraded = bool(xero_error or slack_error)
    if degraded:
        # Leave status=draft so admin can retry. Persist what we got.
        ref.update({
            "order_number": order_number,  # keep the allocated number
            "line_items": lines,
            "xero_draft_id": xero_draft_id,
            "xero_error": xero_error,
            "slack_message_ts": slack_ts,
            "slack_error": slack_error,
            "updated_at": now,
        })
        orders_mod._write_event(order_id, "submit_degraded", {
            "order_number": order_number,
            "xero_error": xero_error,
            "slack_error": slack_error,
        })
        return jsonify({
            "ok": True,
            "degraded": True,
            "order_number": order_number,
            "xero_draft_id": xero_draft_id,
            "slack_message_ts": slack_ts,
            "xero_error": xero_error,
            "slack_error": slack_error,
            "redirect_to": f"/order/{order_id}",
        }), 202

    ref.update({
        "status": "submitted",
        "order_number": order_number,
        "line_items": lines,
        "xero_draft_id": xero_draft_id,
        "slack_message_ts": slack_ts,
        "submitted_at": now,
        "updated_at": now,
        "fallback_contact_used": used_fallback,
    })
    orders_mod._write_event(order_id, "submitted", {
        "order_number": order_number,
        "xero_draft_id": xero_draft_id,
        "slack_message_ts": slack_ts,
        "grand_total_thb": order.get("totals", {}).get("grand_total_thb"),
        "fallback_contact_used": used_fallback,
    })
    log.info("Order %s submitted by %s xero=%s slack=%s",
             order_number, g.user.get("email"), xero_draft_id, slack_ts)
    return jsonify({
        "ok": True,
        "order_number": order_number,
        "xero_draft_id": xero_draft_id,
        "slack_message_ts": slack_ts,
        "redirect_to": f"/order/{order_id}",
    })
