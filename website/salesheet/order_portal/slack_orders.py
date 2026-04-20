"""Slack posts for the order portal.

Uses the same SLACK_BOT_TOKEN env that the public /api/quote flow uses,
but posts to SLACK_ORDER_CHANNEL (from config: C0AUABRBK41 = #orders-wood-products).

- post_new_order(order, submitter_email, portal_base_url) → (ok, ts, err)
- post_threaded_reply(ts, text) → (ok, err)
- post_submit_degraded(order, submitter_email, error_summary) → (ok, ts, err)
  — used when Xero creation fails; still alerts sales team to the new order.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from . import config as cfg

log = logging.getLogger("order_portal.slack")


def _bot_token() -> str:
    return os.environ.get("SLACK_BOT_TOKEN", "").strip()


def _order_channel() -> str:
    # Env wins so ops can override without a redeploy of the config file
    env = os.environ.get("SLACK_ORDER_CHANNEL", "").strip()
    if env:
        return env
    return cfg.slack()["channel_id"]


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


def _thb(n: float | int) -> str:
    return f"{round(n):,} THB"


def post_new_order(
    order: dict[str, Any],
    *,
    submitter_email: str,
    portal_base_url: str,
    xero_draft_id: str | None = None,
) -> tuple[bool, str, str]:
    """Block-Kit message for a freshly submitted order. Returns (ok, ts, err)."""
    order_number = order.get("order_number") or order.get("_id", "")
    customer = order.get("customer", {}) or {}
    totals = order.get("totals", {}) or {}
    line_count = len(order.get("line_items") or [])
    grand = totals.get("grand_total_thb", 0)
    view_url = f"{portal_base_url}/admin/orders/{order.get('_id', '')}"

    fields = [
        {"type": "mrkdwn", "text": f"*Customer*\n{customer.get('name', '—')}"},
        {"type": "mrkdwn", "text": f"*Company*\n{customer.get('company', '—')}"},
        {"type": "mrkdwn", "text": f"*Email*\n<mailto:{customer.get('email', '')}|{customer.get('email', '—')}>"},
        {"type": "mrkdwn", "text": f"*Phone*\n{customer.get('phone', '—')}"},
        {"type": "mrkdwn", "text": f"*Project*\n{customer.get('project_type', '—').capitalize()}"},
        {"type": "mrkdwn", "text": f"*Lines*\n{line_count}"},
        {"type": "mrkdwn", "text": f"*Grand total*\n*{_thb(grand)}*"},
        {"type": "mrkdwn", "text": f"*Submitted by*\n{submitter_email}"},
    ]

    context_bits = [f"Xero draft `{xero_draft_id}`" if xero_draft_id else "Xero draft pending"]

    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🪵 New order {order_number}"}},
        {"type": "section", "fields": fields},
    ]
    if customer.get("notes"):
        notes = str(customer["notes"])[:2500].replace("\n", "\n>")
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Notes*\n>{notes}"}})
    blocks.append({"type": "context", "elements": [
        {"type": "mrkdwn", "text": " · ".join(context_bits)},
    ]})
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "View order"},
                "url": view_url,
                "style": "primary",
            },
        ],
    })

    payload = {
        "channel": _order_channel(),
        "text": f"New order {order_number} from {customer.get('name', 'unknown')} — {_thb(grand)}",
        "blocks": blocks,
        "unfurl_links": False,
        "unfurl_media": False,
    }
    ok, body, err = _post(payload)
    if not ok:
        return False, "", err
    return True, body.get("ts", ""), ""


def post_threaded_reply(ts: str, text: str) -> tuple[bool, str]:
    """Post a plain-text reply in the thread of a previously-posted message."""
    payload = {
        "channel": _order_channel(),
        "thread_ts": ts,
        "text": text,
    }
    ok, _body, err = _post(payload)
    return ok, err
