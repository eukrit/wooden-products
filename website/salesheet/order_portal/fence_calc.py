"""Bridge to the canonical fence calculator at scripts/fence-calculator/.

Resolution order:
  1. order_portal/_fence_calc_bundled/  — staged by cloudbuild.yaml at build time
  2. scripts/fence-calculator/          — repo path for local development

Re-exports FenceConfig, calculate, estimate_shipping. Code outside this
file should `from .fence_calc import FenceConfig, calculate` rather than
poking at sys.path themselves.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_BUNDLED = os.path.join(_HERE, "_fence_calc_bundled")
# scripts/fence-calculator/ from repo root: salesheet -> website -> repo root
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, "..", "..", ".."))
_DEV = os.path.join(_REPO_ROOT, "scripts", "fence-calculator")

if os.path.isdir(_BUNDLED):
    _CALC_DIR = _BUNDLED
elif os.path.isdir(_DEV):
    _CALC_DIR = _DEV
else:
    raise ImportError(
        "fence_calc: cannot locate calculator. Looked at:\n"
        f"  bundled: {_BUNDLED}\n"
        f"  dev:     {_DEV}\n"
        "On Cloud Run cloudbuild.yaml should stage the calculator into "
        "_fence_calc_bundled/. Locally run "
        "scripts/stage-fence-calculator.sh."
    )

if _CALC_DIR not in sys.path:
    sys.path.insert(0, _CALC_DIR)

from calculator import (  # noqa: E402  (sys.path mutation above is intentional)
    FenceConfig,
    LineItem,
    Quote,
    ShippingEstimate,
    calculate,
    estimate_shipping,
    load_params,
)

__all__ = [
    "FenceConfig",
    "LineItem",
    "Quote",
    "ShippingEstimate",
    "calculate",
    "estimate_shipping",
    "load_params",
    "CALC_DIR",
]

CALC_DIR = _CALC_DIR
