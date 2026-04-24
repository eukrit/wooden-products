"""Firebase Authentication — Email/Password + Google sign-in.

Flow:
  1. GET  /auth/login            → renders login page (Firebase JS SDK handles provider UI)
  2. POST /auth/session          → server verifies Firebase ID token, seeds users/{uid}
                                   on first login, writes session cookie, returns redirect URL
  3. POST /auth/logout           → clears session cookie

Also provides decorators:
  - @require_auth   — 401 unless session is valid (verifies against Firebase)
  - @require_role("admin") — 403 unless user has that role in Firestore

Graceful degradation: if FIREBASE_WEB_API_KEY is not set, login page still renders
but shows a banner that sign-in is unavailable. Server-side verification errors
return 503 with a clear message.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from functools import wraps

from flask import (
    abort,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import config as cfg
from . import firestore_client as fs
from . import bp

log = logging.getLogger("order_portal.auth")

# User approval states. Legacy staff docs without this field are treated as
# approved (backfill script sets it explicitly; see scripts/firestore/).
STATUS_PENDING = "pending"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"

# Naive in-process rate limit for /auth/register. Mirrors the pattern in
# server.py's /api/quote. One pod per Cloud Run instance; good enough to
# stop noise in the leads channel without needing Redis.
_REGISTER_WINDOW_S = 60
_REGISTER_MAX_PER_WINDOW = 3
_register_hits: dict[str, list[float]] = {}


def _register_rate_limited(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _register_hits.get(ip, []) if now - t < _REGISTER_WINDOW_S]
    if len(hits) >= _REGISTER_MAX_PER_WINDOW:
        _register_hits[ip] = hits
        return True
    hits.append(now)
    _register_hits[ip] = hits
    return False

_FIREBASE_INITIALIZED = False


def _ensure_firebase_admin():
    """Initialize firebase_admin on first use. Uses ADC (no key file on Cloud Run)."""
    global _FIREBASE_INITIALIZED
    if _FIREBASE_INITIALIZED:
        return
    import firebase_admin  # noqa: WPS433
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "ai-agents-go")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(options={"projectId": project_id})
    _FIREBASE_INITIALIZED = True


def _verify_id_token(id_token: str) -> dict:
    """Return decoded claims. Raises on invalid/expired/revoked."""
    _ensure_firebase_admin()
    from firebase_admin import auth as fb_auth  # noqa: WPS433
    return fb_auth.verify_id_token(id_token, check_revoked=True)


def _upsert_user(uid: str, email: str, display_name: str, provider: str) -> dict:
    """Seed users/{uid} on first login; update last_login_at otherwise.

    Returns the user doc as a dict (with role + status resolved). Staff
    (admin or external_sales based on email domain) are auto-approved.
    Anyone else seeded here (e.g. Google sign-in from an unknown domain)
    is treated as external_sales + approved — the architect flow uses
    _register_architect instead.
    """
    auth_cfg = cfg.auth()
    admin_domain = auth_cfg["admin_email_domain"]
    db = fs.get_db()
    ref = db.collection("users").document(uid)
    snap = ref.get()
    now = datetime.now(timezone.utc)

    if snap.exists:
        data = snap.to_dict() or {}
        ref.update({"last_login_at": now})
        data["last_login_at"] = now
        # Legacy docs without a status field are assumed approved.
        if "status" not in data:
            data["status"] = STATUS_APPROVED
        return data

    role = auth_cfg["default_role_admin"] if email.lower().endswith("@" + admin_domain.lower()) else auth_cfg["default_role_external"]
    doc = {
        "email": email,
        "display_name": display_name or email,
        "role": role,
        "status": STATUS_APPROVED,
        "auth_provider": provider,
        "created_at": now,
        "last_login_at": now,
    }
    ref.set(doc)
    log.info("Seeded users/%s role=%s email=%s", uid, role, email)
    return doc


def _register_architect(
    uid: str,
    email: str,
    display_name: str,
    provider: str,
    profile: dict,
) -> dict:
    """Create an architect user with status=pending. Idempotent: if the doc
    already exists and is non-architect, leave it alone and return it.
    """
    auth_cfg = cfg.auth()
    db = fs.get_db()
    ref = db.collection("users").document(uid)
    snap = ref.get()
    now = datetime.now(timezone.utc)

    if snap.exists:
        data = snap.to_dict() or {}
        # If the user already exists as staff, don't downgrade them.
        if data.get("role") in {auth_cfg["default_role_admin"], auth_cfg["default_role_external"]}:
            return data
        # Re-register architect with fresh profile fields, keep status.
        updates = {
            "display_name": display_name or data.get("display_name") or email,
            "company": profile.get("company", "") or data.get("company", ""),
            "phone": profile.get("phone", "") or data.get("phone", ""),
            "title": profile.get("title", "") or data.get("title", ""),
            "project_context": profile.get("project_context", "") or data.get("project_context", ""),
            "last_login_at": now,
        }
        ref.update(updates)
        data.update(updates)
        if "status" not in data:
            data["status"] = auth_cfg["architect_initial_status"]
        return data

    doc = {
        "email": email,
        "display_name": display_name or email,
        "role": auth_cfg["default_role_architect"],
        "status": auth_cfg["architect_initial_status"],
        "auth_provider": provider,
        "company": profile.get("company", ""),
        "phone": profile.get("phone", ""),
        "title": profile.get("title", ""),
        "project_context": profile.get("project_context", ""),
        "created_at": now,
        "last_login_at": now,
    }
    ref.set(doc)
    log.info(
        "Registered architect users/%s email=%s company=%s",
        uid, email, profile.get("company", ""),
    )
    return doc


def _load_user_doc(uid: str) -> dict | None:
    db = fs.get_db()
    snap = db.collection("users").document(uid).get()
    if not snap.exists:
        return None
    return snap.to_dict()


# ---------- Decorators ----------

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        uid = session.get("uid")
        id_token = session.get("id_token")
        if not (uid and id_token):
            if request.method == "GET" and request.accept_mimetypes.accept_html:
                return redirect(url_for("order_portal.login", next=request.path))
            return jsonify({"ok": False, "error": "unauthenticated"}), 401

        # Re-verify the ID token (cheap — local verification via public keys cache)
        try:
            claims = _verify_id_token(id_token)
        except Exception as exc:
            log.info("Session token invalid (%s) — clearing", exc)
            session.clear()
            if request.method == "GET" and request.accept_mimetypes.accept_html:
                return redirect(url_for("order_portal.login", next=request.path))
            return jsonify({"ok": False, "error": "session_expired"}), 401

        user = _load_user_doc(uid)
        if not user:
            session.clear()
            return jsonify({"ok": False, "error": "user_not_found"}), 401

        g.user = {
            "uid": uid,
            "email": claims.get("email"),
            "display_name": user.get("display_name"),
            "role": user.get("role"),
            "status": user.get("status", STATUS_APPROVED),
        }
        g.impersonating_uid = session.get("impersonating_uid")
        return fn(*args, **kwargs)
    return wrapper


def require_approved(fn):
    """Wraps require_auth. 403 if the user's status is not 'approved'."""
    @wraps(fn)
    @require_auth
    def wrapper(*args, **kwargs):
        status = g.user.get("status")
        if status != STATUS_APPROVED:
            if request.method == "GET" and request.accept_mimetypes.accept_html:
                return redirect(url_for("order_portal.pending"))
            return jsonify({
                "ok": False,
                "error": "not_approved",
                "status": status,
            }), 403
        return fn(*args, **kwargs)
    return wrapper


def require_role(*roles: str):
    def decorator(fn):
        @wraps(fn)
        @require_auth
        def wrapper(*args, **kwargs):
            if g.user.get("role") not in roles:
                if request.accept_mimetypes.accept_html and request.method == "GET":
                    return render_template("auth/forbidden.html", user=g.user, required=roles), 403
                return jsonify({"ok": False, "error": "forbidden", "required_role": list(roles)}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------- Routes ----------

@bp.route("/auth/login", methods=["GET"])
def login():
    """Render login page. Firebase JS SDK handles provider UI client-side."""
    firebase_api_key = os.environ.get("FIREBASE_WEB_API_KEY", "").strip()
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "ai-agents-go").strip()
    auth_cfg = cfg.auth()
    return render_template(
        "auth/login.html",
        firebase_api_key=firebase_api_key,
        firebase_project_id=firebase_project_id,
        firebase_auth_domain=f"{firebase_project_id}.firebaseapp.com",
        next_url=request.args.get("next", "/order/new"),
        config_ready=bool(firebase_api_key),
        auth_providers=auth_cfg["providers"],
        admin_email_domain=auth_cfg["admin_email_domain"],
    )


@bp.route("/auth/session", methods=["POST"])
def session_exchange():
    """Accept Firebase ID token from client, verify, seed/load user, set cookie."""
    data = request.get_json(silent=True) or {}
    id_token = str(data.get("idToken", "")).strip()
    if not id_token:
        return jsonify({"ok": False, "error": "missing_id_token"}), 400

    try:
        claims = _verify_id_token(id_token)
    except Exception as exc:
        log.warning("ID token verification failed: %s", exc)
        return jsonify({"ok": False, "error": "invalid_id_token"}), 401

    uid = claims["uid"]
    email = claims.get("email", "")
    display_name = claims.get("name") or email
    provider = claims.get("firebase", {}).get("sign_in_provider", "unknown")

    user_doc = _upsert_user(uid, email, display_name, provider)

    session.permanent = True
    session["uid"] = uid
    session["id_token"] = id_token
    session["email"] = email
    session["display_name"] = display_name
    session["role"] = user_doc["role"]

    redirect_to = "/admin/orders" if user_doc["role"] == "admin" else "/order/new"
    # Respect `next` if provided and it's a safe path
    next_url = str(data.get("next", "")).strip()
    if next_url.startswith("/") and not next_url.startswith("//"):
        redirect_to = next_url

    return jsonify({"ok": True, "role": user_doc["role"], "redirect_to": redirect_to})


@bp.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.route("/auth/me", methods=["GET"])
@require_auth
def me():
    return jsonify({
        "ok": True,
        "user": g.user,
        "impersonating_uid": g.get("impersonating_uid"),
    })


# ---------- Architect registration + status ----------

@bp.route("/auth/register", methods=["GET"])
def register():
    """Render architect self-registration form."""
    firebase_api_key = os.environ.get("FIREBASE_WEB_API_KEY", "").strip()
    firebase_project_id = os.environ.get("FIREBASE_PROJECT_ID", "ai-agents-go").strip()
    return render_template(
        "auth/register.html",
        firebase_api_key=firebase_api_key,
        firebase_project_id=firebase_project_id,
        firebase_auth_domain=f"{firebase_project_id}.firebaseapp.com",
        config_ready=bool(firebase_api_key),
    )


@bp.route("/auth/register", methods=["POST"])
def register_submit():
    """Accept {idToken, profile{name, company, phone, title, project_context}}.

    Verifies the Firebase ID token (client already created the Firebase user),
    writes users/{uid} with status=pending, posts to Slack architect-leads
    channel, and returns a redirect to the pending page.
    """
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    if _register_rate_limited(ip):
        return jsonify({"ok": False, "error": "rate_limited",
                        "detail": f"Too many registrations from this IP — wait {_REGISTER_WINDOW_S}s."}), 429

    data = request.get_json(silent=True) or {}
    id_token = str(data.get("idToken", "")).strip()
    profile = data.get("profile", {}) or {}
    if not id_token:
        return jsonify({"ok": False, "error": "missing_id_token"}), 400

    try:
        claims = _verify_id_token(id_token)
    except Exception as exc:
        log.warning("Registration id-token verification failed: %s", exc)
        return jsonify({"ok": False, "error": "invalid_id_token"}), 401

    uid = claims["uid"]
    email = claims.get("email", "")
    display_name = (
        str(profile.get("name", "")).strip()
        or claims.get("name")
        or email
    )
    provider = claims.get("firebase", {}).get("sign_in_provider", "unknown")

    # Minimal field validation — keep the 400 messages human-readable.
    for field in ("name", "company"):
        if not str(profile.get(field, "")).strip():
            return jsonify({"ok": False, "error": f"missing_field:{field}"}), 400

    clean_profile = {
        "company": str(profile.get("company", ""))[:200].strip(),
        "phone": str(profile.get("phone", ""))[:40].strip(),
        "title": str(profile.get("title", ""))[:120].strip(),
        "project_context": str(profile.get("project_context", ""))[:2000].strip(),
    }

    user_doc = _register_architect(uid, email, display_name, provider, clean_profile)

    # Fire-and-forget Slack notification. Failures are logged, not surfaced —
    # the registration itself is recorded in Firestore regardless.
    try:
        from . import slack_leads  # lazy import — avoids hard dep at app boot
        ok, err = slack_leads.post_architect_registration(
            uid=uid,
            email=email,
            display_name=display_name,
            profile=clean_profile,
            status=user_doc.get("status", STATUS_PENDING),
            ip=ip,
        )
        if not ok:
            log.warning("Architect Slack post failed: %s", err)
    except Exception as exc:
        log.exception("Architect Slack post crashed: %s", exc)

    # Seed the session so the user lands on /auth/pending without re-typing.
    session.permanent = True
    session["uid"] = uid
    session["id_token"] = id_token
    session["email"] = email
    session["display_name"] = display_name
    session["role"] = user_doc.get("role", "architect")

    return jsonify({
        "ok": True,
        "status": user_doc.get("status", STATUS_PENDING),
        "redirect_to": "/auth/pending",
    })


@bp.route("/auth/status", methods=["GET"])
def status():
    """Lightweight check the configurator calls on page load to decide which
    UI state to show. Never 401/403 — always returns 200 with a shape the
    client can use.
    """
    uid = session.get("uid")
    id_token = session.get("id_token")
    if not (uid and id_token):
        return jsonify({"ok": True, "authenticated": False})

    try:
        _verify_id_token(id_token)
    except Exception:
        session.clear()
        return jsonify({"ok": True, "authenticated": False, "expired": True})

    user = _load_user_doc(uid)
    if not user:
        session.clear()
        return jsonify({"ok": True, "authenticated": False})

    return jsonify({
        "ok": True,
        "authenticated": True,
        "email": user.get("email"),
        "display_name": user.get("display_name"),
        "role": user.get("role"),
        "status": user.get("status", STATUS_APPROVED),
    })


@bp.route("/auth/pending", methods=["GET"])
def pending():
    """Holding page for signed-in users who are not yet approved."""
    uid = session.get("uid")
    email = session.get("email", "")
    display_name = session.get("display_name") or email
    is_signed_in = bool(uid)
    user_status = None
    if is_signed_in:
        user = _load_user_doc(uid) or {}
        user_status = user.get("status", STATUS_APPROVED)
    return render_template(
        "auth/pending.html",
        is_signed_in=is_signed_in,
        email=email,
        display_name=display_name,
        user_status=user_status,
    )
