"""Leka Wood-Products internal order portal.

A Flask Blueprint layered onto the public salesheet app. Adds authenticated
routes /auth/*, /order/*, /admin/* without touching the existing public
pages (/wpc-fence/, /wpc-profile/, /catalog/, /api/quote).

Single source of truth for all config values: data/catalog/order-portal-config.json
"""
from __future__ import annotations

from flask import Blueprint

# Blueprint is the public export. server.py imports + registers it.
# Individual route files (auth.py, catalog_api.py, orders.py, admin.py) attach
# their routes to this blueprint via the `bp` name they import.
bp = Blueprint(
    "order_portal",
    __name__,
    template_folder="../templates",
    static_folder="static",          # <pkg>/static/ — tracked in git
    static_url_path="/static/order",
)

# Route module imports register handlers onto `bp`. Keep imports at bottom to
# avoid circular imports with this module.
from . import auth  # noqa: E402, F401
from . import catalog_api  # noqa: E402, F401
from . import orders  # noqa: E402, F401
from . import order_submit  # noqa: E402, F401
from . import admin  # noqa: E402, F401
from . import placeholders  # noqa: E402, F401
