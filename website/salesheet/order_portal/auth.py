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

    Returns the user doc as a dict (with role resolved).
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
        return data

    role = auth_cfg["default_role_admin"] if email.lower().endswith("@" + admin_domain.lower()) else auth_cfg["default_role_external"]
    doc = {
        "email": email,
        "display_name": display_name or email,
        "role": role,
        "auth_provider": provider,
        "created_at": now,
        "last_login_at": now,
    }
    ref.set(doc)
    log.info("Seeded users/%s role=%s email=%s", uid, role, email)
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
        }
        g.impersonating_uid = session.get("impersonating_uid")
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
