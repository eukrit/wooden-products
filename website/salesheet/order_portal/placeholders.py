"""Phase 1 placeholder routes for /order/new and /admin/orders.

These exist so the auth flow has working redirect targets. They are
replaced with the real implementations in Phase 2–5.
"""
from __future__ import annotations

from flask import g, render_template_string

from . import bp
from .auth import require_auth, require_role


_ORDER_STUB = """
{% extends "layout/base.html" %}
{% block title %}New order — Leka{% endblock %}
{% block content %}
<section style="padding:80px 0">
  <div class="container">
    <span class="eyebrow">Phase 1 · Auth working</span>
    <h1>Hello, {{ g.user.display_name or g.user.email }}</h1>
    <p style="color:var(--lk-navy-60);font-size:18px;margin-top:16px;max-width:640px">
      You're signed in as <strong>{{ g.user.role }}</strong>. The order builder ships in Phase 3 —
      catalog + cart + sticky totals. This placeholder confirms auth + role seeding work end-to-end.
    </p>
    <div style="margin-top:32px;padding:20px;background:var(--lk-navy-06);border-radius:12px;max-width:640px">
      <strong>uid:</strong> <code>{{ g.user.uid }}</code><br>
      <strong>email:</strong> {{ g.user.email }}<br>
      <strong>role:</strong> {{ g.user.role }}
    </div>
  </div>
</section>
{% endblock %}
"""

_ADMIN_STUB = """
{% extends "layout/base.html" %}
{% block title %}Admin orders — Leka{% endblock %}
{% block content %}
<section style="padding:80px 0">
  <div class="container">
    <span class="eyebrow">Phase 1 · Admin access verified</span>
    <h1>Admin dashboard</h1>
    <p style="color:var(--lk-navy-60);font-size:18px;margin-top:16px;max-width:720px">
      Welcome, {{ g.user.display_name or g.user.email }}. The real admin dashboard —
      order list, filters, act-as, confirm/cancel — ships in Phase 5. This placeholder
      confirms the <code>@goco.bz</code> → admin seeding works.
    </p>
    <div style="margin-top:32px;padding:20px;background:var(--lk-navy-06);border-radius:12px;max-width:720px">
      <strong>Phases remaining:</strong><br>
      • Phase 2 — /api/order/catalog with live BoT FX<br>
      • Phase 3 — Order builder UI<br>
      • Phase 4 — Submit → Firestore + Xero + Slack<br>
      • Phase 5 — This dashboard (real)<br>
      • Phase 6 — Deploy secrets + IAM
    </div>
  </div>
</section>
{% endblock %}
"""


@bp.route("/order/new", methods=["GET"])
@require_auth
def order_new_stub():
    return render_template_string(_ORDER_STUB)


@bp.route("/order/", methods=["GET"])
@require_auth
def order_index_stub():
    return render_template_string(_ORDER_STUB)


@bp.route("/admin/orders", methods=["GET"])
@require_role("admin")
def admin_orders_stub():
    return render_template_string(_ADMIN_STUB)


@bp.route("/admin/", methods=["GET"])
@require_role("admin")
def admin_index_stub():
    return render_template_string(_ADMIN_STUB)
