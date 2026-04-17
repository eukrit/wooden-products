"""
Leka Salesheet server — serves static sales sheets and receives quote requests.

Endpoints:
  GET  /                    → landing page (index.html)
  GET  /<path>              → static file / dir index
  POST /api/quote           → validate + forward to Slack #bd-new-leads
  GET  /_healthz            → health check

Environment variables:
  SLACK_BOT_TOKEN           → Slack bot token (xoxb-...) — loaded from GSM
  SLACK_LEAD_CHANNEL        → Slack channel id (default: C07EF698Q1K = #bd-new-leads)
  PORT                      → listen port (Cloud Run sets this)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from flask import Flask, Response, abort, jsonify, request, send_from_directory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("salesheet")

STATIC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "").strip()
SLACK_LEAD_CHANNEL = os.environ.get("SLACK_LEAD_CHANNEL", "C07EF698Q1K").strip()

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = Flask(__name__, static_folder=None)


# ---------- Static serving ----------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_static(path: str):
    """Serve files under /static. Falls back to <dir>/index.html if directory."""
    safe = path.lstrip("/")
    if not safe:
        return send_from_directory(STATIC_ROOT, "index.html")

    full = os.path.normpath(os.path.join(STATIC_ROOT, safe))
    if not full.startswith(STATIC_ROOT):
        abort(403)

    if os.path.isdir(full):
        idx = os.path.join(full, "index.html")
        if os.path.isfile(idx):
            return send_from_directory(full, "index.html")
        abort(404)

    if os.path.isfile(full):
        rel = os.path.relpath(full, STATIC_ROOT)
        return send_from_directory(STATIC_ROOT, rel)

    # try .html fallback
    if os.path.isfile(full + ".html"):
        rel = os.path.relpath(full + ".html", STATIC_ROOT)
        return send_from_directory(STATIC_ROOT, rel)

    abort(404)


# ---------- Health ----------
@app.route("/_healthz")
def healthz():
    return Response("ok", content_type="text/plain")


# ---------- Quote API ----------
REQUIRED_FIELDS = ["name", "email", "projectType", "length", "series"]
ALLOWED_FIELDS = {
    "name", "email", "phone", "company",
    "location", "projectType", "length", "height",
    "series", "color", "gates", "timeline", "message",
    "source", "_hp",  # honeypot
}

PROJECT_TYPES = {"residential", "hospitality", "commercial", "other"}
SERIES_VALUES = {"premium", "classic", "undecided"}

_last_submission_ts: dict[str, float] = {}  # naive per-IP rate limit
RATE_LIMIT_WINDOW_S = 15


@app.route("/api/quote", methods=["POST"])
def api_quote():
    # Rate limit per IP
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    now = time.time()
    last = _last_submission_ts.get(ip, 0)
    if now - last < RATE_LIMIT_WINDOW_S:
        return jsonify({"ok": False, "error": "Please wait a moment before submitting again."}), 429
    _last_submission_ts[ip] = now

    data = request.get_json(silent=True) or {}
    data = {k: v for k, v in data.items() if k in ALLOWED_FIELDS}

    # Honeypot — silently accept but don't forward
    if data.get("_hp"):
        log.info("Honeypot tripped from ip=%s", ip)
        return jsonify({"ok": True}), 200

    # Validate
    missing = [f for f in REQUIRED_FIELDS if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": f"Missing required fields: {', '.join(missing)}"}), 400

    email = str(data.get("email", "")).strip()
    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "Please enter a valid email address."}), 400

    ptype = str(data.get("projectType", "")).lower()
    if ptype not in PROJECT_TYPES:
        return jsonify({"ok": False, "error": "Invalid project type."}), 400

    series = str(data.get("series", "")).lower()
    if series not in SERIES_VALUES:
        return jsonify({"ok": False, "error": "Invalid series selection."}), 400

    # Length sanity
    try:
        length_m = float(str(data.get("length", "0")).strip())
        if length_m <= 0 or length_m > 10000:
            raise ValueError
    except ValueError:
        return jsonify({"ok": False, "error": "Please enter a valid fence length in metres."}), 400

    # Forward to Slack
    ok, slack_err = _post_to_slack(data, ip=ip, length_m=length_m)
    if not ok:
        log.error("Slack forward failed: %s — payload=%s", slack_err, _redact(data))
        # Still return 200 to user; sales will recover from logs.
        # But signal degraded state.
        return jsonify({
            "ok": True,
            "warning": "Your enquiry was recorded. Our sales team will follow up by email.",
            "degraded": True,
        }), 202

    log.info("Quote forwarded to Slack: ip=%s email=%s length=%sm", ip, email, length_m)
    return jsonify({"ok": True}), 200


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    r = dict(data)
    if r.get("email"):
        e = r["email"]
        at = e.find("@")
        if at > 1:
            r["email"] = e[0] + "***" + e[at:]
    if r.get("phone"):
        p = str(r["phone"])
        r["phone"] = p[:4] + "***" + p[-2:] if len(p) > 6 else "***"
    return r


def _post_to_slack(data: dict[str, Any], ip: str, length_m: float) -> tuple[bool, str]:
    if not SLACK_BOT_TOKEN:
        return False, "SLACK_BOT_TOKEN not configured"

    def fv(k: str, default: str = "—") -> str:
        v = str(data.get(k, "") or "").strip()
        return v if v else default

    series_label = {
        "premium": "Premium Co-Extrusion",
        "classic": "Classic WPC",
        "undecided": "Undecided — needs advice",
    }.get(fv("series").lower(), fv("series"))

    type_label = fv("projectType").capitalize()

    fields = [
        {"type": "mrkdwn", "text": f"*Name*\n{fv('name')}"},
        {"type": "mrkdwn", "text": f"*Email*\n<mailto:{fv('email')}|{fv('email')}>"},
        {"type": "mrkdwn", "text": f"*Phone*\n{fv('phone')}"},
        {"type": "mrkdwn", "text": f"*Company*\n{fv('company')}"},
        {"type": "mrkdwn", "text": f"*Project type*\n{type_label}"},
        {"type": "mrkdwn", "text": f"*Location*\n{fv('location')}"},
        {"type": "mrkdwn", "text": f"*Fence length*\n{length_m:g} m"},
        {"type": "mrkdwn", "text": f"*Fence height*\n{fv('height')}"},
        {"type": "mrkdwn", "text": f"*Series*\n{series_label}"},
        {"type": "mrkdwn", "text": f"*Colour*\n{fv('color')}"},
        {"type": "mrkdwn", "text": f"*Gates*\n{fv('gates', '0')}"},
        {"type": "mrkdwn", "text": f"*Timeline*\n{fv('timeline')}"},
    ]

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🌿 New WPC Fence quote request"},
        },
        {"type": "section", "fields": fields[:10]},
        {"type": "section", "fields": fields[10:]},
    ]

    msg = fv("message", "")
    if msg:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Message*\n>{msg[:2500].replace(chr(10), chr(10)+'>')}"},
        })

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"Submitted from `{fv('source', 'salesheet.leka.studio')}` · IP `{ip}`"},
        ],
    })

    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Email back"},
                "url": f"mailto:{fv('email')}?subject=" + urllib.parse.quote(
                    f"Re: WPC Fence enquiry — {fv('name', 'your project')}"
                ),
                "style": "primary",
            },
        ],
    })

    fallback_text = (
        f"New WPC Fence quote request from {fv('name')} ({fv('email')}) — "
        f"{length_m:g}m {series_label} · {type_label} · {fv('location')}"
    )

    payload = {
        "channel": SLACK_LEAD_CHANNEL,
        "text": fallback_text,
        "blocks": blocks,
        "unfurl_links": False,
        "unfurl_media": False,
    }

    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read())
    except urllib.error.URLError as exc:
        return False, f"network_error: {exc}"
    except Exception as exc:
        return False, f"unexpected_error: {exc!r}"

    if not resp.get("ok"):
        return False, f"slack_error: {resp.get('error')}"
    return True, ""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
