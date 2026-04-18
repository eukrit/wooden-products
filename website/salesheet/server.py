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

import base64
import hashlib
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image").strip()
RENDER_DAILY_BUDGET = int(os.environ.get("RENDER_DAILY_BUDGET", "200"))
RENDER_RATE_LIMIT_S = int(os.environ.get("RENDER_RATE_LIMIT_S", "20"))

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
# Fence-specific (legacy wpc-fence modal)
FENCE_REQUIRED = ["name", "email", "projectType", "length", "series"]
# Generic (shared /quote/ form + future sales sheets)
GENERIC_REQUIRED = ["name", "email", "message"]

ALLOWED_FIELDS = {
    # Common
    "name", "email", "phone", "company", "message", "source",
    "product", "productName",
    # Project context
    "location", "projectType", "timeline", "quantity",
    # WPC-fence legacy
    "length", "height", "series", "color", "gates",
    # WPC-fence configurator (extended)
    "bayWidth", "boardGap", "fenceRun", "singleGates", "doubleGates",
    "totalLength", "sceneImageUrl",
    # Honeypot
    "_hp",
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

    # Route by product: wpc-fence (legacy modal) uses strict fence validation;
    # anything else uses the generic schema.
    product = str(data.get("product", "")).strip().lower()
    is_fence = product == "wpc-fence" or (
        not product and str(data.get("series", "")).strip()  # legacy modal didn't send product
    )

    required = FENCE_REQUIRED if is_fence else GENERIC_REQUIRED
    missing = [f for f in required if not str(data.get(f, "")).strip()]
    if missing:
        return jsonify({"ok": False, "error": f"Missing required fields: {', '.join(missing)}"}), 400

    email = str(data.get("email", "")).strip()
    if not EMAIL_RE.match(email):
        return jsonify({"ok": False, "error": "Please enter a valid email address."}), 400

    length_m = None
    if is_fence:
        ptype = str(data.get("projectType", "")).lower()
        if ptype not in PROJECT_TYPES:
            return jsonify({"ok": False, "error": "Invalid project type."}), 400

        series = str(data.get("series", "")).lower()
        if series not in SERIES_VALUES:
            return jsonify({"ok": False, "error": "Invalid series selection."}), 400

        try:
            length_m = float(str(data.get("length", "0")).strip())
            if length_m <= 0 or length_m > 10000:
                raise ValueError
        except ValueError:
            return jsonify({"ok": False, "error": "Please enter a valid fence length in metres."}), 400
    else:
        # Generic: optional projectType from select — accept unknown values gracefully
        msg = str(data.get("message", "")).strip()
        if len(msg) < 10:
            return jsonify({"ok": False, "error": "Please include at least 10 characters in the project description."}), 400

    # Forward to Slack
    if is_fence:
        ok, slack_err = _post_to_slack(data, ip=ip, length_m=length_m)
    else:
        ok, slack_err = _post_generic_to_slack(data, ip=ip)
    if not ok:
        log.error("Slack forward failed: %s — payload=%s", slack_err, _redact(data))
        # Still return 200 to user; sales will recover from logs.
        # But signal degraded state.
        return jsonify({
            "ok": True,
            "warning": "Your enquiry was recorded. Our sales team will follow up by email.",
            "degraded": True,
        }), 202

    log.info(
        "Quote forwarded to Slack: ip=%s email=%s product=%s length=%s",
        ip, email, product or "general", length_m if length_m is not None else "—",
    )
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

    # Configurator fields (optional — only present for the new configurator flow)
    fence_run  = fv("fenceRun", "")
    bay_width  = fv("bayWidth", "")
    board_gap  = fv("boardGap", "")
    single_g   = fv("singleGates", "")
    double_g   = fv("doubleGates", "")
    total_len  = fv("totalLength", "")
    has_configurator = any([fence_run, bay_width, board_gap, single_g, double_g])

    gates_line = fv("gates", "0")
    if single_g or double_g:
        gates_line = f"{single_g or 0} × single (1.2 m)  ·  {double_g or 0} × double (2.4 m)"

    length_line = f"{length_m:g} m"
    if has_configurator and fence_run and total_len:
        length_line = f"Fence run {fence_run} m + gates → *Total {total_len} m*"

    fields = [
        {"type": "mrkdwn", "text": f"*Name*\n{fv('name')}"},
        {"type": "mrkdwn", "text": f"*Email*\n<mailto:{fv('email')}|{fv('email')}>"},
        {"type": "mrkdwn", "text": f"*Phone*\n{fv('phone')}"},
        {"type": "mrkdwn", "text": f"*Company*\n{fv('company')}"},
        {"type": "mrkdwn", "text": f"*Project type*\n{type_label}"},
        {"type": "mrkdwn", "text": f"*Location*\n{fv('location')}"},
        {"type": "mrkdwn", "text": f"*Fence length*\n{length_line}"},
        {"type": "mrkdwn", "text": f"*Fence height*\n{fv('height')}"},
        {"type": "mrkdwn", "text": f"*Series*\n{series_label}"},
        {"type": "mrkdwn", "text": f"*Colour*\n{fv('color')}"},
        {"type": "mrkdwn", "text": f"*Gates*\n{gates_line}"},
        {"type": "mrkdwn", "text": f"*Timeline*\n{fv('timeline')}"},
    ]
    if has_configurator:
        fields.extend([
            {"type": "mrkdwn", "text": f"*Bay width*\n{bay_width} m"},
            {"type": "mrkdwn", "text": f"*Board gap*\n{board_gap} cm"},
        ])

    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🌿 New WPC Fence quote request"},
        },
        {"type": "section", "fields": fields[:10]},
    ]
    if len(fields) > 10:
        blocks.append({"type": "section", "fields": fields[10:]})

    msg = fv("message", "")
    if msg:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Message*\n>{msg[:2500].replace(chr(10), chr(10)+'>')}"},
        })

    scene_img = fv("sceneImageUrl", "")
    if scene_img and (scene_img.startswith("http://") or scene_img.startswith("https://")):
        blocks.append({
            "type": "image",
            "image_url": scene_img,
            "alt_text": "Configurator scene render",
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


def _post_generic_to_slack(data: dict[str, Any], ip: str) -> tuple[bool, str]:
    """Forward a generic (non-fence) quote enquiry to Slack."""
    if not SLACK_BOT_TOKEN:
        return False, "SLACK_BOT_TOKEN not configured"

    def fv(k: str, default: str = "—") -> str:
        v = str(data.get(k, "") or "").strip()
        return v if v else default

    product_name = fv("productName", "") or fv("product", "general enquiry")

    fields = [
        {"type": "mrkdwn", "text": f"*Name*\n{fv('name')}"},
        {"type": "mrkdwn", "text": f"*Email*\n<mailto:{fv('email')}|{fv('email')}>"},
        {"type": "mrkdwn", "text": f"*Phone*\n{fv('phone')}"},
        {"type": "mrkdwn", "text": f"*Company*\n{fv('company')}"},
        {"type": "mrkdwn", "text": f"*Project type*\n{fv('projectType').capitalize() if fv('projectType') != '—' else '—'}"},
        {"type": "mrkdwn", "text": f"*Location*\n{fv('location')}"},
        {"type": "mrkdwn", "text": f"*Timeline*\n{fv('timeline')}"},
        {"type": "mrkdwn", "text": f"*Quantity / area*\n{fv('quantity')}"},
    ]

    blocks: list[dict[str, Any]] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"🌿 New quote request — {product_name}"}},
        {"type": "section", "fields": fields[:8]},
        {"type": "section", "text": {"type": "mrkdwn",
            "text": f"*Message*\n>{fv('message')[:2500].replace(chr(10), chr(10)+'>')}"}},
        {"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"Submitted from `{fv('source', 'salesheet.leka.studio/quote/')}` · Product `{fv('product', 'general')}` · IP `{ip}`"},
        ]},
        {"type": "actions", "elements": [{
            "type": "button",
            "text": {"type": "plain_text", "text": "Email back"},
            "url": f"mailto:{fv('email')}?subject=" + urllib.parse.quote(
                f"Re: {product_name} enquiry — {fv('name', 'your project')}"
            ),
            "style": "primary",
        }]},
    ]

    fallback_text = (
        f"New quote request from {fv('name')} ({fv('email')}) — "
        f"{product_name} · {fv('projectType')} · {fv('location')}"
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


# ---------- Scene Render (Gemini 2.5 Flash Image / "Nanobanana") ----------
_SCENE_DESCRIPTIONS = {
    "residential":  "modern Thai villa with tropical garden and paved driveway",
    "hospitality":  "boutique resort pool terrace with teak decking and palms",
    "hospital":     "contemporary hospital courtyard with wayfinding and soft landscaping",
    "school":       "international school playground perimeter with green lawn",
    "resort":       "beachfront luxury resort with sea view and coconut palms",
}
_SERIES_LABEL = {
    "premium": "Premium Co-Extrusion (shield-wrapped composite, embossed woodgrain)",
    "classic": "Classic WPC (solid wood-composite, 3D embossed woodgrain)",
}

# In-memory cache: {sha256: {"base64": str, "ts": float}}
_render_cache: dict[str, dict[str, Any]] = {}
# In-memory budget counter: {yyyymmdd: int}
_render_budget: dict[str, int] = {}
_render_last_ts: dict[str, float] = {}


def _today_key() -> str:
    return time.strftime("%Y%m%d", time.gmtime())


def _spec_hash(spec: dict[str, Any]) -> str:
    keys = ("series", "height", "bayWidth", "gap", "colorCode", "scene")
    canonical = "|".join(f"{k}={spec.get(k, '')}" for k in keys)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _build_render_prompt(spec: dict[str, Any], has_ref: bool = False) -> str:
    scene_key = str(spec.get("scene", "residential")).lower()
    scene_desc = _SCENE_DESCRIPTIONS.get(scene_key, _SCENE_DESCRIPTIONS["residential"])
    series_desc = _SERIES_LABEL.get(str(spec.get("series", "premium")).lower(), _SERIES_LABEL["premium"])
    height = spec.get("height", 2.0)
    bay = spec.get("bayWidth", 2.0)
    gap = int(spec.get("gap", 0) or 0)
    color_name = spec.get("colorName", "Teak")
    color_hex = spec.get("colorHex", "#A06A3A")
    gap_line = (
        "solid privacy fence with zero gap between horizontal 148 mm WPC boards (tongue-and-groove)"
        if gap == 0
        else f"slatted / louvered fence with a {gap} cm horizontal gap between each 148 mm WPC board"
    )
    ref_line = (
        " The attached reference image shows the EXACT woodgrain finish and colour of the "
        "manufacturer's WPC board — reproduce that grain pattern and tone faithfully on every board."
        if has_ref else ""
    )
    return (
        f"Photorealistic architectural photograph of a {height} m tall {gap_line}. "
        f"Board finish: {color_name} ({color_hex}) — {series_desc}.{ref_line} "
        f"Bay width {bay} m between 80 x 80 mm matte-black extruded aluminium posts. "
        f"Context: installed as a perimeter at a {scene_desc}. "
        f"Golden-hour natural light, wide-angle lens, 3:2 aspect ratio, high detail, realistic shadows."
    )


def _load_swatch_reference(color_code: str) -> tuple[str | None, str | None]:
    """Return (base64_jpeg, mime) for the manufacturer woodgrain crop, or (None, None) if missing."""
    if not color_code:
        return None, None
    safe = "".join(ch for ch in color_code.lower() if ch.isalnum() or ch == "-")
    path = os.path.join(STATIC_ROOT, "wpc-fence", "images", "swatches", f"{safe}.jpg")
    if not os.path.isfile(path):
        return None, None
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii"), "image/jpeg"
    except OSError:
        return None, None


def _call_gemini_image(prompt: str, ref_b64: str | None = None, ref_mime: str | None = None) -> tuple[bytes | None, str]:
    """Call Gemini 2.5 Flash Image (aka 'Nanobanana'). Returns (png_bytes, error).

    If a reference image is supplied, it is passed as an additional inlineData part so the
    model grounds the generated scene on the real manufacturer woodgrain texture.
    """
    if not GEMINI_API_KEY:
        return None, "Gemini API key not configured"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_IMAGE_MODEL}:generateContent?key={urllib.parse.quote(GEMINI_API_KEY)}"
    )
    parts: list[dict[str, Any]] = [{"text": prompt}]
    if ref_b64 and ref_mime:
        parts.append({"inlineData": {"mimeType": ref_mime, "data": ref_b64}})
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "temperature": 0.8,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            err_body = str(exc)
        return None, f"gemini_http_{exc.code}: {err_body}"
    except urllib.error.URLError as exc:
        return None, f"network_error: {exc}"
    except Exception as exc:
        return None, f"unexpected_error: {exc!r}"

    try:
        parts = body["candidates"][0]["content"]["parts"]
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"]), ""
        return None, "no_image_in_response"
    except (KeyError, IndexError, ValueError) as exc:
        return None, f"response_parse_error: {exc!r}"


@app.route("/api/render-scene", methods=["POST"])
def api_render_scene():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    now = time.time()
    last = _render_last_ts.get(ip, 0)
    if now - last < RENDER_RATE_LIMIT_S:
        wait = int(RENDER_RATE_LIMIT_S - (now - last))
        return jsonify({"ok": False, "error": f"Please wait {wait}s before rendering again."}), 429
    _render_last_ts[ip] = now

    today = _today_key()
    if _render_budget.get(today, 0) >= RENDER_DAILY_BUDGET:
        return jsonify({"ok": False, "error": "Daily render budget reached. Try again tomorrow or request a quote directly."}), 429

    data = request.get_json(silent=True) or {}
    allowed = {"series", "height", "bayWidth", "gap", "colorCode", "colorName", "colorHex", "scene"}
    spec = {k: v for k, v in data.items() if k in allowed}

    scene = str(spec.get("scene", "")).lower()
    if scene not in _SCENE_DESCRIPTIONS:
        return jsonify({"ok": False, "error": "Invalid scene."}), 400
    spec["scene"] = scene

    h = _spec_hash(spec)
    cached = _render_cache.get(h)
    if cached:
        log.info("Render cache hit: hash=%s ip=%s", h[:8], ip)
        return jsonify({"ok": True, "imageBase64": cached["base64"], "cached": True}), 200

    ref_b64, ref_mime = _load_swatch_reference(str(spec.get("colorCode", "")))
    prompt = _build_render_prompt(spec, has_ref=bool(ref_b64))
    log.info("Render request: hash=%s scene=%s series=%s ref=%s ip=%s",
             h[:8], scene, spec.get("series"), "yes" if ref_b64 else "no", ip)
    png_bytes, err = _call_gemini_image(prompt, ref_b64=ref_b64, ref_mime=ref_mime)
    if err or not png_bytes:
        log.error("Render failed: err=%s", err)
        return jsonify({"ok": False, "error": "Render failed — please try again or pick another scene."}), 502

    b64 = base64.b64encode(png_bytes).decode("ascii")
    _render_cache[h] = {"base64": b64, "ts": now}
    _render_budget[today] = _render_budget.get(today, 0) + 1
    return jsonify({"ok": True, "imageBase64": b64, "cached": False}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port, debug=False)
