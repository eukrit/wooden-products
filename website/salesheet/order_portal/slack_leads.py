"""Slack posts for architect/registration leads.

Separate from slack_orders.py so the channel + formatting evolve
independently. Uses the same SLACK_BOT_TOKEN + Web API endpoint.

Channel: #new-leads-wood-products (from order-portal-config.json →
slack.architect_leads_channel_id, env SLACK_ARCHITECT_LEADS_CHANNEL
overrides).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from . import config as cfg

log = logging.getLogger("order_portal.slack_leads")


def _bot_token() -> str:
    return os.environ.get("SLACK_BOT_TOKEN", "").strip()


def _leads_channel() -> str:
    env = os.environ.get("SLACK_ARCHITECT_LEADS_CHANNEL", "").strip()
    if env:
        return env
    return cfg.slack().get("architect_leads_channel_id", "").strip()


def _post(payload: dict[str, Any]) -> tuple[bool, dict[str, Any], str]:
    token = _bot_token()
    if not token:
        return False, {}, "SLACK_BOT_TOKEN not configured"
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
    except urllib.error.URLError as exc:
        return False, {}, f"network_error: {exc}"
    except Exception as exc:
        return False, {}, f"unexpected_error: {exc!r}"
    if not body.get("ok"):
        return False, body, f"slack_error: {body.get('error')}"
    return True, body, ""


def post_architect_registration(
    *,
    uid: str,
    email: str,
    display_name: str,
    profile: dict[str, Any],
    status: str,
    ip: str,
) -> tuple[bool, str]:
    """Post a fresh architect registration to the leads channel."""
    channel = _leads_channel()
    if not channel:
        return False, "architect_leads_channel_id not configured"

    company = profile.get("company", "—") or "—"
    phone = profile.get("phone", "—") or "—"
    title = profile.get("title", "—") or "—"
    ctx = profile.get("project_context", "") or ""

    fields = [
        {"type": "mrkdwn", "text": f"*Name*\n{display_name or '—'}"},
        {"type": "mrkdwn", "text": f"*Email*\n<mailto:{email}|{email}>"},
        {"type": "mrkdwn", "text": f"*Company*\n{company}"},
        {"type": "mrkdwn", "text": f"*Phone*\n{phone}"},
        {"type": "mrkdwn", "text": f"*Title*\n{title}"},
        {"type": "mrkdwn", "text": f"*Status*\n`{status}`"},
    ]

    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": "👷 New architect registration"}},
        {"type": "section", "fields": fields},
    ]
    if ctx:
        trimmed = ctx[:2000].replace("\n", "\n>")
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Project context*\n>{trimmed}"},
        })
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Firebase uid `{uid}` · submitted from `salessheet.leka.studio/auth/register` · IP `{ip}`"},
        ],
    })
    blocks.append({
        "type": "actions",
        "block_id": f"architect_decision::{uid}",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "✅ Approve"},
                "style": "primary",
                "action_id": "architect_approve",
                "value": uid,
            },
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "❌ Reject"},
                "style": "danger",
                "action_id": "architect_reject",
                "value": uid,
                "confirm": {
                    "title": {"type": "plain_text", "text": "Reject this architect?"},
                    "text": {"type": "mrkdwn", "text": f"They won't see retail pricing. You can re-approve later by editing Firestore `users/{uid}.status`."},
                    "confirm": {"type": "plain_text", "text": "Reject"},
                    "deny": {"type": "plain_text", "text": "Cancel"},
                },
            },
        ],
    })
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text":
                "Web fallback: <https://salessheet.leka.studio/admin/orders|/admin/orders> · "
                "API: `POST /admin/architects/" + uid + "/{approve,reject}`"},
        ],
    })

    fallback = f"New architect registration: {display_name} ({email}) — {company}"
    payload = {
        "channel": channel,
        "text": fallback,
        "blocks": blocks,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    ok, _body, err = _post(payload)
    if not ok:
        log.warning("post_architect_registration failed: %s", err)
        return False, err
    log.info("Architect registration posted to Slack: uid=%s email=%s", uid, email)
    return True, ""


def post_architect_decision(
    *,
    uid: str,
    email: str,
    display_name: str,
    decision: str,
    actor_email: str,
    reason: str = "",
) -> tuple[bool, str]:
    """Post a one-liner when an admin approves/rejects an architect."""
    channel = _leads_channel()
    if not channel:
        return False, "architect_leads_channel_id not configured"
    icon = "✅" if decision == "approved" else "❌"
    text = (
        f"{icon} *{decision.capitalize()}* — {display_name} ({email}) "
        f"by {actor_email}"
    )
    if reason:
        text += f" — _{reason[:300]}_"
    payload = {"channel": channel, "text": text, "unfurl_links": False}
    ok, _body, err = _post(payload)
    return ok, err
