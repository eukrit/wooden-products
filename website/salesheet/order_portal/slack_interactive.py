"""Slack interactivity endpoint — handles button clicks on the architect
registration message.

  POST /slack/interactive   (Slack-signed; verified via SLACK_SIGNING_SECRET)

Slack posts a form-encoded payload containing a JSON `payload` field. We:
  1. Verify the request signature (HMAC-SHA256 of `v0:{ts}:{raw_body}`).
  2. Reject anything older than 5 minutes (replay protection).
  3. Authorise — only Slack member IDs in
     order-portal-config.json → slack.architect_admin_user_ids may decide.
  4. Map action_id (`architect_approve` / `architect_reject`) → call
     admin.architect_decision_core(uid, decision, …).
  5. Use the payload's `response_url` to replace the original message with
     a "✅ Approved by …" / "❌ Rejected by …" status block.

Required env: SLACK_SIGNING_SECRET (mounted from GSM in cloudbuild.yaml).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

from flask import Response, jsonify, request

from . import bp, config as cfg
from . import admin as admin_mod

log = logging.getLogger("order_portal.slack_interactive")

_REPLAY_WINDOW_S = 60 * 5  # Slack's standard


def _signing_secret() -> str:
    return os.environ.get("SLACK_SIGNING_SECRET", "").strip()


def _verify_signature(raw_body: bytes, ts: str, sig: str) -> bool:
    """Return True iff the Slack signature matches.

    Constant-time comparison; rejects missing-config, bad timestamp, or
    timestamp older than the replay window.
    """
    secret = _signing_secret()
    if not secret or not ts or not sig:
        return False
    try:
        ts_int = int(ts)
    except ValueError:
        return False
    if abs(time.time() - ts_int) > _REPLAY_WINDOW_S:
        return False
    base = b"v0:" + ts.encode() + b":" + raw_body
    expected = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _is_admin(user_id: str) -> bool:
    allowed = cfg.slack().get("architect_admin_user_ids", []) or []
    return user_id in allowed


def _post_response(response_url: str, payload: dict[str, Any]) -> None:
    """Update the original message via Slack's response_url. Best-effort."""
    if not response_url:
        return
    req = urllib.request.Request(
        response_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            r.read()
    except (urllib.error.URLError, Exception) as exc:
        log.warning("response_url POST failed: %s", exc)


def _decision_status_block(
    *,
    icon: str,
    decision_label: str,
    user_display: str,
    user_email: str,
    actor_label: str,
    reason: str,
) -> list[dict[str, Any]]:
    text = f"{icon} *{decision_label}* — {user_display} ({user_email}) by {actor_label}"
    if reason:
        text += f" — _{reason[:300]}_"
    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": "Decision recorded in Firestore. The architect will see indicative pricing on the configurator immediately if approved."},
        ]},
    ]


@bp.route("/slack/interactive", methods=["POST"])
def slack_interactive():
    raw_body = request.get_data(cache=False)
    ts = request.headers.get("X-Slack-Request-Timestamp", "")
    sig = request.headers.get("X-Slack-Signature", "")

    if not _verify_signature(raw_body, ts, sig):
        log.warning("Slack signature verification failed (ts=%s)", ts)
        return Response("invalid signature", status=401)

    payload_str = request.form.get("payload", "")
    if not payload_str:
        return Response("missing payload", status=400)

    try:
        payload = json.loads(payload_str)
    except json.JSONDecodeError:
        return Response("invalid json", status=400)

    if payload.get("type") != "block_actions":
        return jsonify({"ok": True, "ignored": True})

    actions = payload.get("actions") or []
    if not actions:
        return jsonify({"ok": True, "ignored": True})

    action = actions[0]
    action_id = action.get("action_id", "")
    target_uid = str(action.get("value", "")).strip()
    user_id = (payload.get("user") or {}).get("id", "")
    user_name = (payload.get("user") or {}).get("username") or (payload.get("user") or {}).get("name", "")
    response_url = payload.get("response_url", "")

    if not target_uid:
        return jsonify({"ok": False, "error": "missing_uid"})

    if not _is_admin(user_id):
        log.warning("Unauthorised Slack click: user=%s action=%s", user_id, action_id)
        _post_response(response_url, {
            "replace_original": False,
            "response_type": "ephemeral",
            "text": ":no_entry: You're not in the approver allowlist. Ask Eukrit if you should be.",
        })
        return jsonify({"ok": False, "error": "forbidden"})

    if action_id == "architect_approve":
        decision = "approved"
    elif action_id == "architect_reject":
        decision = "rejected"
    else:
        return jsonify({"ok": False, "error": "unknown_action", "action_id": action_id})

    actor_label = f"Slack:{user_name or user_id} ({user_id})"
    body, _code = admin_mod.architect_decision_core(
        target_uid,
        decision,
        actor_uid=user_id,
        actor_label=actor_label,
        reason="Decided via Slack button",
        post_followup_to_slack=False,  # we replace the original message instead
    )

    if not body.get("ok"):
        _post_response(response_url, {
            "replace_original": False,
            "response_type": "ephemeral",
            "text": f":warning: Couldn't apply decision: {body.get('error', 'unknown')}",
        })
        return jsonify({"ok": False, "error": body.get("error")})

    user_info = body.get("user") or {}
    blocks = _decision_status_block(
        icon="✅" if decision == "approved" else "❌",
        decision_label=decision.capitalize(),
        user_display=user_info.get("display_name") or user_info.get("email") or target_uid,
        user_email=user_info.get("email") or "",
        actor_label=actor_label,
        reason="",
    )
    _post_response(response_url, {
        "replace_original": True,
        "blocks": blocks,
        "text": f"{decision.capitalize()} by {actor_label}",
    })

    return jsonify({"ok": True, "uid": target_uid, "status": decision})
