"""Tiny alias route — Phase 3 + Phase 5 now own the real handlers.

/order/new + /order/<id> are in orders.py (Phase 3).
/admin/orders is in admin.py (Phase 5). /admin/ just redirects there.
"""
from __future__ import annotations

from flask import redirect

from . import bp
from .auth import require_role


@bp.route("/admin/", methods=["GET"], endpoint="admin_root")
@require_role("admin")
def admin_root():
    return redirect("/admin/orders")
