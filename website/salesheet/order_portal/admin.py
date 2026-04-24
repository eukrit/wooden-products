"""Admin dashboard routes.

  GET  /admin/orders                    list view with filters
  GET  /admin/orders/<id>               detail + audit log
  POST /admin/orders/<id>/confirm       submitted → confirmed (Xero AUTHORISED + Slack thread)
  POST /admin/orders/<id>/cancel        any → cancelled (Xero VOIDED + Slack thread)
  POST /admin/orders/<id>/retry-submit  re-run the degraded-path flow
  POST /admin/orders/<id>/act-as        start impersonating the order's creator
  POST /admin/end-act-as                clear impersonation

All routes require role=admin. Every mutation writes an order_events row
with both actor_uid (real admin) and acted_as_uid (if impersonating).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from flask import abort, g, jsonify, render_template, request, session, url_for

from . import bp, config as cfg, slack_orders, xero_client
from .auth import require_role
from . import firestore_client as fs
from . import orders as orders_mod
from . import order_submit as submit_mod

log = logging.getLogger("order_portal.admin")


def _orders_coll():
    return fs.get_db().collection("orders")


def _users_by_uid() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for doc in fs.get_db().collection("users").stream():
        out[doc.id] = doc.to_dict() or {}
    return out


# ---------- List ----------

@bp.route("/admin/orders", methods=["GET"], endpoint="admin_orders_list")
@require_role("admin")
def admin_orders_list():
    """Filtered list of all orders. Overrides the placeholder in placeholders.py."""
    status_filter = (request.args.get("status") or "").strip()
    uid_filter = (request.args.get("uid") or "").strip()
    date_from = (request.args.get("from") or "").strip()
    date_to = (request.args.get("to") or "").strip()

    q = _orders_coll()
    if status_filter:
        q = q.where("status", "==", status_filter)
    if uid_filter:
        q = q.where("created_by_uid", "==", uid_filter)

    docs = list(q.order_by("updated_at", direction="DESCENDING").limit(200).stream())

    rows: list[dict[str, Any]] = []
    for snap in docs:
        d = snap.to_dict() or {}
        d["_id"] = snap.id
        # Cheap client-side date filter — Firestore composite indexes are overkill for this scale
        if date_from and d.get("updated_at") and d["updated_at"].isoformat() < date_from:
            continue
        if date_to and d.get("updated_at") and d["updated_at"].isoformat() > date_to + "T23:59:59":
            continue
        rows.append(d)

    users = _users_by_uid()
    for r in rows:
        uid = r.get("created_by_uid")
        r["_creator_email"] = (users.get(uid, {}) or {}).get("email", uid)

    return render_template(
        "admin/orders_list.html",
        rows=rows,
        users=list(users.items()),
        filters={
            "status": status_filter,
            "uid": uid_filter,
            "from": date_from,
            "to": date_to,
        },
    )


# ---------- Detail ----------

@bp.route("/admin/orders/<order_id>", methods=["GET"], endpoint="admin_order_detail")
@require_role("admin")
def admin_order_detail(order_id: str):
    order = orders_mod._load_order(order_id)
    if not order:
        abort(404)

    events_raw = list(
        orders_mod._ref(order_id)
        .collection("order_events")
        .order_by("timestamp", direction="DESCENDING")
        .limit(200)
        .stream()
    )
    events = []
    for snap in events_raw:
        e = snap.to_dict() or {}
        e["_id"] = snap.id
        events.append(e)

    users = _users_by_uid()
    creator = users.get(order.get("created_by_uid", ""), {}) or {}
    return render_template(
        "admin/order_detail.html",
        order=order,
        order_id=order_id,
        events=events,
        users=users,
        creator=creator,
    )


# ---------- State transitions ----------

def _post_thread(order: dict[str, Any], text: str) -> tuple[bool, str]:
    ts = order.get("slack_message_ts")
    if not ts:
        return True, "no_slack_thread"  # not an error — original Slack post may have failed
    return slack_orders.post_threaded_reply(ts, text)


@bp.route("/admin/orders/<order_id>/confirm", methods=["POST"], endpoint="admin_confirm")
@require_role("admin")
def admin_confirm(order_id: str):
    order = orders_mod._load_order(order_id)
    if not order:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if order.get("status") != "submitted":
        return jsonify({"ok": False, "error": "wrong_state", "detail": f"status={order.get('status')}"}), 409

    xero_error = None
    if order.get("xero_draft_id") and xero_client.is_configured():
        try:
            xero_client.update_invoice_status(
                order["xero_draft_id"],
                cfg.xero()["confirmed_status"],
            )
        except Exception as exc:
            xero_error = str(exc)[:300]
            log.exception("Xero confirm failed for %s", order_id)

    actor = g.user.get("email", "admin")
    _post_thread(order, f"✅ Confirmed by {actor}" + (f" (Xero error: {xero_error})" if xero_error else ""))

    orders_mod._ref(order_id).update({
        "status": "confirmed",
        "confirmed_at": datetime.now(timezone.utc),
        "confirmed_by_uid": g.user["uid"],
        "updated_at": datetime.now(timezone.utc),
        "xero_confirm_error": xero_error,
    })
    orders_mod._write_event(order_id, "confirmed", {
        "xero_error": xero_error,
    })
    return jsonify({"ok": True, "xero_error": xero_error})


@bp.route("/admin/orders/<order_id>/cancel", methods=["POST"], endpoint="admin_cancel")
@require_role("admin")
def admin_cancel(order_id: str):
    order = orders_mod._load_order(order_id)
    if not order:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if order.get("status") == "cancelled":
        return jsonify({"ok": False, "error": "already_cancelled"}), 409

    xero_error = None
    if order.get("xero_draft_id") and xero_client.is_configured():
        try:
            xero_client.update_invoice_status(
                order["xero_draft_id"],
                cfg.xero()["cancelled_status"],
            )
        except Exception as exc:
            xero_error = str(exc)[:300]
            log.exception("Xero cancel failed for %s", order_id)

    actor = g.user.get("email", "admin")
    reason = (request.form.get("reason") or "").strip() or (request.get_json(silent=True) or {}).get("reason", "")
    _post_thread(order, f"❌ Cancelled by {actor}" + (f" — {reason}" if reason else ""))

    orders_mod._ref(order_id).update({
        "status": "cancelled",
        "cancelled_at": datetime.now(timezone.utc),
        "cancelled_by_uid": g.user["uid"],
        "cancel_reason": reason or None,
        "updated_at": datetime.now(timezone.utc),
        "xero_cancel_error": xero_error,
    })
    orders_mod._write_event(order_id, "cancelled", {
        "reason": reason,
        "xero_error": xero_error,
    })
    return jsonify({"ok": True, "xero_error": xero_error})


@bp.route("/admin/orders/<order_id>/retry-submit", methods=["POST"], endpoint="admin_retry_submit")
@require_role("admin")
def admin_retry_submit(order_id: str):
    """Re-run the submit flow for an order still in draft with a recorded failure."""
    order = orders_mod._load_order(order_id)
    if not order:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if order.get("status") != "draft":
        return jsonify({"ok": False, "error": "already_done", "detail": f"status={order.get('status')}"}), 409
    # Delegate to the existing submit handler — it re-validates + retries Xero + Slack
    return submit_mod.order_submit(order_id)


# ---------- Impersonation ----------

@bp.route("/admin/orders/<order_id>/act-as", methods=["POST"], endpoint="admin_act_as")
@require_role("admin")
def admin_act_as(order_id: str):
    order = orders_mod._load_order(order_id)
    if not order:
        return jsonify({"ok": False, "error": "not_found"}), 404
    target_uid = order.get("created_by_uid")
    if not target_uid:
        return jsonify({"ok": False, "error": "no_creator"}), 400
    session["impersonating_uid"] = target_uid
    orders_mod._write_event(order_id, "admin_impersonated", {"target_uid": target_uid})
    log.info("Admin %s now acting as %s (order %s)", g.user.get("email"), target_uid, order_id)
    return jsonify({"ok": True, "impersonating_uid": target_uid})


@bp.route("/admin/end-act-as", methods=["POST"], endpoint="admin_end_act_as")
@require_role("admin")
def admin_end_act_as():
    session.pop("impersonating_uid", None)
    return jsonify({"ok": True})


# ---------- Architect approval ----------

def _architect_decision(uid: str, decision: str) -> tuple[dict, int]:
    """Shared helper for approve/reject. Returns (json_body, http_code)."""
    from . import slack_leads  # lazy

    db = fs.get_db()
    ref = db.collection("users").document(uid)
    snap = ref.get()
    if not snap.exists:
        return {"ok": False, "error": "user_not_found"}, 404

    user = snap.to_dict() or {}
    now = datetime.now(timezone.utc)
    reason = ""
    if request.is_json:
        reason = str((request.get_json(silent=True) or {}).get("reason", "")).strip()
    else:
        reason = str(request.form.get("reason", "")).strip()

    if decision == "approved":
        ref.update({
            "status": "approved",
            "approved_by_uid": g.user["uid"],
            "approved_at": now,
            "rejected_reason": None,
            "updated_at": now,
        })
    else:
        ref.update({
            "status": "rejected",
            "rejected_by_uid": g.user["uid"],
            "rejected_at": now,
            "rejected_reason": reason or None,
            "updated_at": now,
        })

    try:
        slack_leads.post_architect_decision(
            uid=uid,
            email=user.get("email", ""),
            display_name=user.get("display_name", user.get("email", "")),
            decision=decision,
            actor_email=g.user.get("email", "admin"),
            reason=reason,
        )
    except Exception as exc:
        log.warning("Slack post for architect decision failed: %s", exc)

    log.info("Architect %s → %s by %s", uid, decision, g.user.get("email"))
    return {"ok": True, "uid": uid, "status": decision}, 200


@bp.route("/admin/architects/<uid>/approve", methods=["POST"], endpoint="admin_architect_approve")
@require_role("admin")
def admin_architect_approve(uid: str):
    body, code = _architect_decision(uid, "approved")
    return jsonify(body), code


@bp.route("/admin/architects/<uid>/reject", methods=["POST"], endpoint="admin_architect_reject")
@require_role("admin")
def admin_architect_reject(uid: str):
    body, code = _architect_decision(uid, "rejected")
    return jsonify(body), code
