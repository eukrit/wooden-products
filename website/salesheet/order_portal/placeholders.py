"""Remaining placeholder routes.

/order/new and /order/<id> are now served by orders.py (Phase 3).
/admin/orders and /admin/ still stubs until Phase 5.
"""
from __future__ import annotations

from flask import render_template_string

from . import bp
from .auth import require_role


_ADMIN_STUB = """
{% extends "layout/base.html" %}
{% block title %}Admin orders — Leka{% endblock %}
{% block content %}
<section style="padding:80px 0">
  <div class="container">
    <span class="eyebrow">Phase 5 · Coming soon</span>
    <h1>Admin dashboard</h1>
    <p style="color:var(--lk-navy-60);font-size:18px;margin-top:16px;max-width:720px">
      Welcome, {{ g.user.display_name or g.user.email }}. The real admin dashboard —
      order list, filters, act-as, confirm/cancel — ships in Phase 5.
    </p>
    <div style="margin-top:32px;padding:20px;background:var(--lk-navy-06);border-radius:12px;max-width:720px">
      <strong>Phases remaining:</strong><br>
      • Phase 4 — Submit → Firestore + Xero + Slack<br>
      • Phase 5 — This dashboard (real)<br>
      • Phase 6 — Deploy secrets + IAM
    </div>
    <div style="margin-top:24px">
      <a href="/order/new" class="nav-cta" style="background:var(--lk-purple);color:var(--lk-white);padding:12px 24px;border-radius:999px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;font-size:13px;text-decoration:none">Create a new order →</a>
    </div>
  </div>
</section>
{% endblock %}
"""


@bp.route("/admin/orders", methods=["GET"])
@require_role("admin")
def admin_orders_stub():
    return render_template_string(_ADMIN_STUB)


@bp.route("/admin/", methods=["GET"])
@require_role("admin")
def admin_index_stub():
    return render_template_string(_ADMIN_STUB)
