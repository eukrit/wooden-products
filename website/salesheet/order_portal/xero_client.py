"""Xero API client — lean vendored copy of
accounting-automation/integrations/xero/client.py.

Kept in-tree because Cloud Build's docker context is `website/salesheet/`,
so we can't directly import from the sibling repo.

Owns Xero auth in one place: loads tokens from Secret Manager (or the
XERO_TOKENS_JSON env var injected via --set-secrets), refreshes when
expired, and writes refreshed tokens back to the secret. Shared secret
`xero-tokens` with accounting-automation — both services stay in sync.

Env (all from Secret Manager in Cloud Run):
  XERO_CLIENT_ID, XERO_CLIENT_SECRET
  XERO_TOKENS_JSON              preferred; contains {access_token, refresh_token, tenant_id, ...}
  XERO_TOKENS_SECRET_NAME       default: xero-tokens
  XERO_TENANT_ID                optional override
  GCP_PROJECT_ID                default: ai-agents-go
  XERO_DEFAULT_ACCOUNT_CODE     default: 200
"""
from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

log = logging.getLogger("order_portal.xero")

_TOKEN_URL = "https://identity.xero.com/connect/token"
_API_BASE = "https://api.xero.com/api.xro/2.0"


class XeroError(Exception):
    pass


@dataclass
class XeroTokens:
    access_token: str
    refresh_token: str
    expires_at: datetime
    tenant_id: str | None = None

    def is_expired(self, skew_seconds: int = 60) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at - timedelta(seconds=skew_seconds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat(),
            "tenant_id": self.tenant_id,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "XeroTokens":
        access = d["access_token"]
        refresh = d["refresh_token"]
        if "expires_at" in d:
            expires_at = datetime.fromisoformat(d["expires_at"])
        else:
            # Upstream blob may only have expires_in — treat as expired so
            # we refresh on first use.
            expires_at = datetime.now(timezone.utc)
        return cls(
            access_token=access,
            refresh_token=refresh,
            expires_at=expires_at,
            tenant_id=d.get("tenant_id"),
        )


def is_configured() -> bool:
    return bool(os.environ.get("XERO_CLIENT_ID") and os.environ.get("XERO_CLIENT_SECRET"))


def _project_id() -> str:
    return os.environ.get("GCP_PROJECT_ID", "ai-agents-go")


def _tokens_secret_name() -> str:
    return os.environ.get("XERO_TOKENS_SECRET_NAME", "xero-tokens")


def _secretmanager_client():
    from google.cloud import secretmanager  # lazy
    from google.auth import compute_engine  # lazy
    # Bypass GOOGLE_APPLICATION_CREDENTIALS which may be bound to a secret
    # blob rather than a file path on this service.
    creds = compute_engine.Credentials()
    return secretmanager.SecretManagerServiceClient(credentials=creds)


def _load_tokens() -> XeroTokens:
    raw_env = os.environ.get("XERO_TOKENS_JSON", "").strip()
    if raw_env.startswith("{"):
        return XeroTokens.from_dict(json.loads(raw_env))

    secret = _tokens_secret_name()
    if secret:
        try:
            client = _secretmanager_client()
            name = f"projects/{_project_id()}/secrets/{secret}/versions/latest"
            payload = client.access_secret_version(request={"name": name}).payload.data
            return XeroTokens.from_dict(json.loads(payload.decode("utf-8")))
        except Exception as exc:
            log.warning("Secret Manager load failed (%s) — falling back to file", exc)

    path = os.environ.get(
        "XERO_TOKENS_FILE",
        os.path.expanduser(
            "~/OneDrive/Documents/Claude Code/Credentials Claude Code/xero_tokens.json"
        ),
    )
    if not os.path.exists(path):
        raise XeroError(f"No Xero tokens at {path} and Secret Manager unavailable")
    with open(path, "r", encoding="utf-8") as fh:
        return XeroTokens.from_dict(json.load(fh))


def _save_tokens(tokens: XeroTokens) -> None:
    secret = _tokens_secret_name()
    if secret:
        try:
            client = _secretmanager_client()
            parent = f"projects/{_project_id()}/secrets/{secret}"
            client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": json.dumps(tokens.to_dict()).encode("utf-8")},
                }
            )
            log.info("Wrote refreshed Xero tokens back to %s", secret)
            return
        except Exception as exc:
            log.error("Secret Manager save failed: %s", exc)


def _refresh(tokens: XeroTokens) -> XeroTokens:
    cid = os.environ.get("XERO_CLIENT_ID")
    csec = os.environ.get("XERO_CLIENT_SECRET")
    if not (cid and csec):
        raise XeroError("XERO_CLIENT_ID / XERO_CLIENT_SECRET not configured")

    auth = base64.b64encode(f"{cid}:{csec}".encode()).decode()
    res = requests.post(
        _TOKEN_URL,
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"grant_type": "refresh_token", "refresh_token": tokens.refresh_token},
        timeout=20,
    )
    if not res.ok:
        raise XeroError(f"Token refresh failed: {res.status_code} {res.text[:300]}")
    payload = res.json()
    refreshed = XeroTokens(
        access_token=payload["access_token"],
        refresh_token=payload["refresh_token"],
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 1800))),
        tenant_id=tokens.tenant_id,
    )
    _save_tokens(refreshed)
    return refreshed


def _ensure_fresh() -> XeroTokens:
    tokens = _load_tokens()
    if tokens.is_expired():
        tokens = _refresh(tokens)
    if not tokens.tenant_id:
        tokens.tenant_id = os.environ.get("XERO_TENANT_ID")
        if not tokens.tenant_id:
            raise XeroError("Xero tenant_id missing — set XERO_TENANT_ID or store it in xero-tokens")
    return tokens


def _request(method: str, path: str, *, json_body: dict[str, Any] | None = None,
             params: dict[str, Any] | None = None) -> dict[str, Any]:
    tokens = _ensure_fresh()
    res = requests.request(
        method=method,
        url=f"{_API_BASE}{path}",
        headers={
            "Authorization": f"Bearer {tokens.access_token}",
            "Xero-tenant-id": tokens.tenant_id or "",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        params=params,
        json=json_body,
        timeout=30,
    )
    if not res.ok:
        raise XeroError(f"Xero {method} {path} → {res.status_code}: {res.text[:400]}")
    return res.json()


# ---------- High-level operations ----------

def upsert_contact(
    email: str,
    name: str,
    *,
    company: str | None = None,
    phone: str | None = None,
) -> str:
    """Find or create a Xero Contact by email. Returns ContactID."""
    found = _request("GET", f'/Contacts?where=EmailAddress=="{email}"')
    contacts = found.get("Contacts") or []
    if contacts:
        return contacts[0]["ContactID"]

    payload: dict[str, Any] = {
        "Contacts": [
            {
                "Name": company or name,
                "FirstName": name.split(" ", 1)[0] if name else "",
                "LastName": " ".join(name.split(" ", 1)[1:]) or None,
                "EmailAddress": email,
            }
        ]
    }
    if phone:
        payload["Contacts"][0]["Phones"] = [{"PhoneType": "DEFAULT", "PhoneNumber": phone}]
    created = _request("PUT", "/Contacts", json_body=payload)
    return created["Contacts"][0]["ContactID"]


def ensure_item(sku: str, name: str) -> None:
    """Ensure an Item with Code=sku exists. Skips if already present."""
    try:
        found = _request("GET", f"/Items/{sku}")
        if found.get("Items"):
            return
    except XeroError as exc:
        # 404 = not found, any other = propagate
        if "404" not in str(exc):
            raise
    _request("PUT", "/Items", json_body={
        "Items": [{"Code": sku, "Name": name[:50]}],
    })
    log.info("Created Xero Item %s", sku)


def create_invoice(
    *,
    contact_id: str,
    reference: str,
    items: list[dict[str, Any]],
    tracking_category: str | None = None,
    tracking_option: str | None = None,
    status: str = "DRAFT",
    currency_code: str = "THB",
) -> str:
    """Create a Xero Invoice. Returns InvoiceID.

    items: [{sku, name, quantity, unit_price_thb, tax_type?}]
    """
    account_code = os.environ.get("XERO_DEFAULT_ACCOUNT_CODE", "200")

    line_items = []
    for it in items:
        line: dict[str, Any] = {
            "ItemCode": it["sku"],
            "Description": it["name"],
            "Quantity": float(it["quantity"]),
            "UnitAmount": float(it["unit_price_thb"]),
            "AccountCode": account_code,
        }
        if tracking_category and tracking_option:
            line["Tracking"] = [{"Name": tracking_category, "Option": tracking_option}]
        if it.get("tax_type"):
            line["TaxType"] = it["tax_type"]
        line_items.append(line)

    payload = {
        "Invoices": [
            {
                "Type": "ACCREC",  # Accounts Receivable = outgoing invoice to customer
                "Contact": {"ContactID": contact_id},
                "Date": datetime.now(timezone.utc).date().isoformat(),
                "DueDate": (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat(),
                "LineItems": line_items,
                "CurrencyCode": currency_code.upper(),
                "Status": status.upper(),
                "Reference": reference,
            }
        ]
    }
    created = _request("POST", "/Invoices", json_body=payload)
    invoice_id = created["Invoices"][0]["InvoiceID"]
    log.info("Created Xero Invoice %s ref=%s", invoice_id, reference)
    return invoice_id


def update_invoice_status(invoice_id: str, status: str) -> None:
    """Valid transitions: DRAFT → SUBMITTED → AUTHORISED → PAID (or → VOIDED)."""
    _request("POST", f"/Invoices/{invoice_id}", json_body={
        "Invoices": [{"InvoiceID": invoice_id, "Status": status.upper()}],
    })
    log.info("Updated Xero Invoice %s → status=%s", invoice_id, status)
