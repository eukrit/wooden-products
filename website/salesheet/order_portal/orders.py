"""Order draft CRUD + detail view.

Routes:
  POST /order/new              create a draft order, redirect to /order/<id>
  GET  /order/<id>             render the order builder for this draft
  GET  /order/<id>.json        current draft state as JSON (client re-hydration)
  PATCH /order/<id>            debounced autosave from the client
  POST /order/<id>/validate    return {ok, errors} for the submit-button gate

The actual /order/<id>/submit endpoint lives in orders_submit.py (Phase 4).
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from flask import abort, g, jsonify, redirect, render_template, request

from . import bp, pricing
from .auth import require_auth
from . import firestore_client as fs

log = logging.getLogger("order_portal.orders")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_ALLOWED_ORDER_STATUSES = {"draft", "submitted", "confirmed", "cancelled"}


# ---------- Helpers ----------

def _new_draft_id() -> str:
    return "draft-" + uuid.uuid4().hex[:12]


def _empty_draft(uid: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "order_number": None,
        "status": "draft",
        "created_by_uid": uid,
        "customer": {
            "name": "",
            "email": "",
            "phone": "",
            "company": "",
            "billing_address": "",
            "project_type": "",
            "notes": "",
        },
        "line_items": [],
        "totals": {
            "subtotal_thb": 0.0,
            "vat_thb": 0.0,
            "grand_total_thb": 0.0,
        },
        "created_at": now,
        "updated_at": now,
    }


def _ref(order_id: str):
    return fs.get_db().collection("orders").document(order_id)


def _load_order(order_id: str) -> dict[str, Any] | None:
    snap = _ref(order_id).get()
    if not snap.exists:
        return None
    doc = snap.to_dict() or {}
    doc["_id"] = order_id
    return doc


def _can_access(order: dict[str, Any], user: dict[str, Any]) -> bool:
    if user.get("role") == "admin":
        return True
    return order.get("created_by_uid") == user.get("uid")


def _write_event(order_id: str, event_type: str, detail: dict[str, Any]) -> None:
    try:
        _ref(order_id).collection("order_events").add({
            "event_type": event_type,
            "actor_uid": g.user.get("uid"),
            "acted_as_uid": g.get("impersonating_uid"),
            "detail": detail,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as exc:
        log.warning("Failed to write order_event %s for %s: %s", event_type, order_id, exc)


# ---------- Customer + line validation ----------

_REQUIRED_CUSTOMER = ["name", "email", "phone", "company", "billing_address", "project_type"]
_PROJECT_TYPES = {"residential", "hospitality", "commercial", "institutional", "other"}


def _validate_submit(order: dict[str, Any], role: str) -> tuple[bool, list[str]]:
    errors: list[str] = []

    c = order.get("customer", {}) or {}
    for f in _REQUIRED_CUSTOMER:
        if not str(c.get(f, "")).strip():
            errors.append(f"customer.{f} required")
    if c.get("email") and not _EMAIL_RE.match(c["email"].strip()):
        errors.append("customer.email invalid format")
    if c.get("project_type") and c["project_type"] not in _PROJECT_TYPES:
        errors.append(f"customer.project_type must be one of {sorted(_PROJECT_TYPES)}")

    lines = order.get("line_items") or []
    if not lines:
        errors.append("at least one line item required")
    for i, ln in enumerate(lines):
        sku = ln.get("sku")
        qty = ln.get("quantity_pcs", 0)
        unit = ln.get("unit_price_thb", 0)
        landed = ln.get("landed_cost_thb_per_m")
        if not sku:
            errors.append(f"line[{i}].sku required")
        if not qty or qty <= 0:
            errors.append(f"line[{i}].quantity_pcs must be > 0")
        if unit is None or unit <= 0:
            errors.append(f"line[{i}].unit_price_thb must be > 0")
        if landed is None:
            errors.append(f"line[{i}] has no landed_cost_thb_per_m — pricing missing")
            continue
        ok, msg = pricing.validate_line_gm(float(unit), float(landed), role)
        if not ok:
            errors.append(f"line[{i}] {msg}")
    return len(errors) == 0, errors


# ---------- Routes ----------

@bp.route("/order/new", methods=["GET", "POST"], endpoint="order_new")
@require_auth
def order_new():
    """Create a draft order and redirect to its detail page."""
    order_id = _new_draft_id()
    draft = _empty_draft(g.user["uid"])
    _ref(order_id).set(draft)
    _write_event(order_id, "created", {})
    log.info("Created draft %s by %s", order_id, g.user.get("email"))
    # POST = JS client (Alpine.js fetch), expects JSON. GET = browser navigation
    # (e.g. window.location.href after login), expects a 302 to the detail page.
    if request.method == "POST":
        return jsonify({"ok": True, "order_id": order_id, "redirect_to": f"/order/{order_id}"})
    return redirect(f"/order/{order_id}")


@bp.route("/order/<order_id>", methods=["GET"], endpoint="order_detail")
@require_auth
def order_detail(order_id: str):
    order = _load_order(order_id)
    if not order:
        abort(404)
    if not _can_access(order, g.user):
        abort(403)

    return render_template(
        "order/detail.html",
        order_id=order_id,
        order=order,
        gm_floor=pricing.gm_floor_for_role(g.user["role"]),
        vat_pct=pricing.cfg.pricing()["vat_pct"],
    )


@bp.route("/order/<order_id>.json", methods=["GET"], endpoint="order_detail_json")
@require_auth
def order_detail_json(order_id: str):
    order = _load_order(order_id)
    if not order:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if not _can_access(order, g.user):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    # Convert Firestore timestamps to ISO strings for JSON
    for k in ("created_at", "updated_at", "submitted_at"):
        if order.get(k) and hasattr(order[k], "isoformat"):
            order[k] = order[k].isoformat()
    return jsonify({"ok": True, "order": order})


@bp.route("/order/<order_id>", methods=["PATCH"], endpoint="order_update")
@require_auth
def order_update(order_id: str):
    order = _load_order(order_id)
    if not order:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if not _can_access(order, g.user):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    if order.get("status") != "draft":
        return jsonify({"ok": False, "error": "immutable", "detail": f"status={order.get('status')}"}), 409

    data = request.get_json(silent=True) or {}
    patch: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}

    # Allowed top-level keys: customer (merged), line_items (replaced), totals (replaced)
    if "customer" in data and isinstance(data["customer"], dict):
        allowed = {"name", "email", "phone", "company", "billing_address", "project_type", "notes"}
        patch["customer"] = {k: v for k, v in data["customer"].items() if k in allowed}
        # Merge, not replace — preserve untouched fields
        merged = dict(order.get("customer", {}))
        merged.update(patch["customer"])
        patch["customer"] = merged

    if "line_items" in data and isinstance(data["line_items"], list):
        allowed_line = {
            "sku", "name", "w", "t", "len", "colour", "colour_code", "colour_hex",
            "finish", "quantity_pcs", "quantity_m", "unit_price_thb",
            "landed_cost_thb_per_m", "gm_percent", "line_total_thb",
        }
        clean_lines = []
        for ln in data["line_items"]:
            if not isinstance(ln, dict):
                continue
            clean_lines.append({k: v for k, v in ln.items() if k in allowed_line})
        patch["line_items"] = clean_lines

    if "totals" in data and isinstance(data["totals"], dict):
        allowed_tot = {"subtotal_thb", "vat_thb", "grand_total_thb"}
        patch["totals"] = {k: v for k, v in data["totals"].items() if k in allowed_tot}

    _ref(order_id).update(patch)

    # Log meaningful events (not per-keystroke autosave noise)
    if "line_items" in patch:
        _write_event(order_id, "lines_updated", {"count": len(patch["line_items"])})

    return jsonify({"ok": True})


@bp.route("/order/<order_id>/validate", methods=["POST"], endpoint="order_validate")
@require_auth
def order_validate(order_id: str):
    """Return whether this draft can be submitted."""
    order = _load_order(order_id)
    if not order:
        return jsonify({"ok": False, "error": "not_found"}), 404
    if not _can_access(order, g.user):
        return jsonify({"ok": False, "error": "forbidden"}), 403
    ok, errors = _validate_submit(order, g.user["role"])
    return jsonify({"ok": ok, "errors": errors})
