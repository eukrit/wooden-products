# Changelog

All notable changes to this project will be documented in this file.

## [0.10.1] - 2026-04-24

### Added — Architect portal follow-ons

- Slack `#new-leads-wood-products` channel id wired
  (`C0B0JTXMRK2`).
- Premium vs Classic series pricing now differs: Premium uses
  `LKP-FN-161-20` at full rate, Classic uses the same SKU ×
  `fence_classic_price_ratio` (0.75) until a Heritage fence SKU lands
  in the vendor map. `breakdown.series` and `breakdown.price_ratio`
  are surfaced in the `/api/configurator/price` response.
- `/auth/register` IP rate-limit: 3 attempts per 60 s → 429.

## [0.10.0] - 2026-04-24

### Added — Firebase Auth on WPC Fence Configurator

- **Architect self-registration** (`GET/POST /auth/register`). Firebase
  Email/Password account creation with a profile capture form (name,
  company, phone, title, project context). The server seeds
  `users/{uid}` with `status=pending` and role `architect`, then posts
  a structured notification to Slack `#new-leads-wood-products` (new
  channel; id populated in `order-portal-config.json`) for manual
  review.
- **Admin approve/reject routes.** `POST /admin/architects/<uid>/approve`
  and `/reject` flip the architect's status and post a follow-up in the
  leads channel. Full Slack interactivity (one-click buttons) is
  deferred; admins approve via curl or the Firestore console for now.
- **Live retail pricing in the configurator.** New endpoint
  `GET /api/configurator/price` (behind a new `require_approved`
  decorator in `order_portal/auth.py`) computes indicative retail
  THB from the fence-board SKU (`LKP-FN-161-20`), structural uplift,
  and gate hardware. The configurator fetches `/auth/status` on load,
  renders one of four states in the totals panel (guest / pending /
  rejected / approved), and debounces a pricing refresh at 300 ms on
  every input change.
- **Status field on users.** `users/{uid}.status ∈
  {pending, approved, rejected}`. Legacy staff docs without a status
  are treated as approved at runtime; a backfill script
  (`scripts/firestore/backfill_user_status.py`, dry-run flag) writes
  the field explicitly.
- **Pending holding page.** `/auth/pending` shows a status-aware card;
  `require_approved` redirects HTML GETs there automatically.

### Files changed

- `website/salesheet/order_portal/auth.py`,
  `configurator_api.py` (new), `slack_leads.py` (new),
  `pricing.py`, `admin.py`, `__init__.py`
- `website/salesheet/templates/auth/register.html` (new),
  `templates/auth/pending.html` (new)
- `website/salesheet/wpc-fence/configurator/index.html`
- `data/catalog/order-portal-config.json` (v1.1.0)
- `scripts/firestore/backfill_user_status.py` (new)

### Pre-prod TODO

- Create Slack channel `#new-leads-wood-products`, invite `@ai_agents`,
  paste channel id into
  `data/catalog/order-portal-config.json.slack.architect_leads_channel_id`
  (or set `SLACK_ARCHITECT_LEADS_CHANNEL`).
- Run `python scripts/firestore/backfill_user_status.py` in each env.
- Verify Firebase Email/Password provider is enabled in the
  `ai-agents-go` project.

## [0.9.2] - 2026-04-22

### Fixed — WPC Fence Configurator — layout polish

- **Trim plank no longer overflows the aluminium top rail.** Previously
  the trim plank was drawn at full 148 mm height above `infillTop`,
  relying on the top rail to clip the overhang — which meant the plank
  visibly extended above the frame whenever the trim visible height was
  small (e.g. 20 mm at a 4 cm board gap). Now the trim plank is drawn
  at exactly `trimVisibleMm` tall, flush with the bottom of the top
  rail, so it always stays inside the frame. The amber dashed cut-line
  still marks the installer's on-site trim.
- **Render card header.** The "Render scene" button and its helper text
  moved into the `<h5>` header as a flex row (`.render-head`), freeing
  a whole row of vertical space above the scene picker and the render
  result.
- **Removed the busy "✂ Trim plank — N mm visible" SVG callout.** The
  dashed cut-line on the plank itself + the "Includes N trim plank(s)"
  line in the totals strip carry the message without crowding the
  drawing, especially at small trim heights.

### Changed — Mobile configurator order

- On ≤ 860 px viewports the configurator now stacks **live preview →
  configure panel → render-in-a-scene**, instead of preview → render →
  configure. Implemented via `display: contents` on `.config-main` + CSS
  `order` on the flattened children, so the desktop two-column grid is
  untouched.

## [0.9.1] - 2026-04-21

### Fixed — WPC Fence sales page — palette + configurator polish

- **Colour palette** (`website/salesheet/wpc-fence/index.html`) — moved
  `background-size: cover`, `background-position: center`, and
  `background-repeat: no-repeat` onto the `.swatch-chip` class and split each
  chip's inline style into explicit `background-color` + `background-image`
  declarations. The prior `background:#HEX url(...) center/cover` shorthand
  silently swallowed the image on some browsers / at some cache states, so
  the palette was rendering as flat colour blocks instead of manufacturer
  woodgrain crops.
- **Hero image preload** — added `<link rel="preload" as="image" href="images/141.jpg">`
  so the hero background paints in the first frame instead of popping in
  after layout.

### Added — Configurator (`website/salesheet/wpc-fence/configurator/`)

- **Random plank pattern per board** — each plank renders the manufacturer
  swatch through a nested `<svg>` viewport with a seeded random offset
  (1.6× wider / 1.4× taller than the plank), so each board reads as a
  distinct extruded length instead of one repeating tile. Seed is derived
  from the current spec so the pattern is stable across idle re-renders.
- **Trim plank at top** — the leftover space above the last full plank is
  now filled with a trim plank (field-cut on site). Drawn as a full 148 mm
  plank extending above the infill top; the top rail is painted AFTER the
  planks so the overhang is naturally clipped. A dashed amber cut-line and a
  `✂ Trim plank — N mm visible · cut on site` badge mark the trim position.
- **Bay-width and fence-height dimension lines** — architectural-style
  dimensions outside the posts (horizontal above for bay width, vertical on
  the right for height) with extension lines, arrowheads, and boxed labels.
- **Board count update** — `boardsPerBay` now rounds up to include the trim
  plank. The totals strip shows an additional line "Includes N trim plank(s)
  — field-cut on site" when a trim is present. The Request-a-Quote spec
  preview also surfaces `Boards / bay` and `Total boards` with a trim
  breakdown.
- **SVG layer order** — rails are now drawn in the correct paint order
  (bottom rail before planks, top rail after planks) so the trim plank's
  overhang is covered cleanly.

### Removed

- `Powered by Gemini` eyebrow tag next to the "Render in a scene" heading
  in the configurator — the render is still Gemini-backed, the tag just
  wasn't earning its pixels.

## [0.9.0] - 2026-04-21

### Added — WPC Deck Collection sales sheet (/wpc-deck/)

- `website/salesheet/wpc-deck/index.html` — full Leka Design System
  sales sheet mirroring the `/wpc-fence/` template. Manrope type scale,
  navy/cream/purple/magenta/amber tokens, full-scroll section order: nav,
  hero, stats, manifesto, range (2 up), spec table (13 rows), material
  science, substructure (joist + clip), 3 configurations, 4-step install
  (with inline SVG assembly diagram), gallery, 8 colour palette, 5
  applications, 9-row comparison vs timber / porcelain / painted concrete,
  warranty (15 yr / 10 yr structural + ΔE retention), CTA, footer, quote
  modal.
- Leka-branded product codes:
  - **LKD-P-140** Premium Deck Board — 140 × 20 mm reversible
  - **LKD-C-097** Classic Deck Board — 97 × 20 mm reversible
- Leka 8-colour standard palette reused from `/wpc-fence/`; swatch
  images copied to `wpc-deck/images/swatches/`.
- Hero / range / config / gallery imagery sourced from the existing
  Leka `wpc-profile` co-extrusion photo library, then enriched in place
  by `scripts/enrich_wpc_deck_images.py` (Gemini 3 Pro Image Preview)
  with two prompt variants: "product card" (seamless pale background,
  centred product, soft shadow, 1024×1024) for the 2 range cards, and
  "context scene" (preserve setting, tighten composition, recentre,
  clean artefacts) for the 7 hero / config / gallery shots. No vendor
  imagery on the public page.
- `wpc-deck/SOURCE_MAPPING.md` — **internal-only** mapping of Leka SKUs
  to upstream vendor codes (DECK-140, Deck-002), MOQs, lead times, and
  warranty pass-through rules. Excluded from the Docker build via an
  updated `website/salesheet/.dockerignore` pattern so it never ships
  to the static container.
- `website/salesheet/Dockerfile` — new `COPY wpc-deck static/wpc-deck`
  layer. `website/salesheet/index.html` landing page now lists three
  collections (profiles, deck, fence). `.claude/launch.json` gains a
  `wpc-deck-site` entry for local preview on port 8086.

### Added — Maxis Wood competitor catalog scrape (internal)

- `scripts/scrapers/maxiswood_scrape.js` — Node + playwright-core
  scraper that drives the system Google Chrome (Playwright's bundled
  Chromium lacks a VC++ runtime on this host). Renders each iTopPlus
  AngularJS-rendered category page, saves the post-render HTML and a
  full-page PNG, and writes a per-category JSON so the run survives
  Windows libuv `new_time >= loop->time` crashes mid-batch.
- `scripts/scrapers/maxiswood_extract.py` — BeautifulSoup pass over the
  rendered HTML that pulls structured fields per category: description,
  properties, advantages, specifications table (product_code, dimension,
  profile, color, price), remarks, colors note, warranty note, brochure
  PDF, and product gallery images (site-chrome filtered out).
- Outputs under `data/parsed/maxiswood/`:
  `maxiswood_catalog.json` (11 categories, nested),
  `maxiswood_catalog.csv` (27 flat SKU-level rows),
  `maxiswood_images.csv` (123 image URLs), `README.md` (per-category
  summary). Raw rendered HTML + full-page screenshots in
  `data/raw/maxiswood/`.

### Copy / warranty guardrails

- Warranty copy follows `website/salesheet/README.md §8`:
  structural-vs-surface split (never bundled), measurable ΔE fade
  thresholds, explicit exclusions list, 60-day written-notice claim
  process, pass-through disclaimer. Structural years (15 / 10) are
  Leka's underwritten figures; surface years (5 / 3) match the upstream
  manufacturer's published limited warranty and require the anti-UV top
  coat at install for the Premium 5-yr figure.
- No vendor names, no vendor SKUs, no non-English characters on the
  public page. Verified via `grep -i fence wpc-deck/index.html` (empty).

## [0.8.1] - 2026-04-20

### Added — Extra catalog coverage (fuzzy-matcher aliases + quotation importer)

Two small wins on top of the 6-phase delivery to lift catalog coverage.

- **`order_portal/pricing.py::lookup_sku_entry`** — adds `WG ↔ 2D` and
  `EM ↔ 3D` finish-suffix aliasing. Heritage taxonomy SKUs use `WG`/`EM`;
  the SKU-map uses `2D`/`3D` (two generations of the same vendor
  data). Matcher now handles both.
  - **Coverage: 8 → 14 taxonomy SKUs auto-price from the SKU-map.** New
    matches: Heritage Deck 140×25 WG/EM, 140×20 WG/EM, Heritage Cladding
    148×21 WG/EM.
  - Anhui pricing update (handled offline) will cover the remaining ~35.

- **`scripts/import_quotation_pricing.py` (new)** — one-shot utility to
  import priced line items from `data/parsed/quotations.json` into
  Firestore `catalog_pricing/{sku}` as admin pricing overrides.
  - Reads 10 priced quote lines across 5 non-Aolo vendors (leo-nature,
    qihome, chinese-teak-vendor, sentai, ks-wood).
  - Converts each source currency (USD, CNY) to THB via live frankfurter
    + `fx_buffer_pct` from the config — same FX source the order portal uses.
  - Default dry-run; `--write` flag pushes to Firestore. `--skus a,b,c`
    for selective import. `--actor` to customise the updated_by field.
  - Stores `unit_price_thb` (full retail from the quote) + traceability
    fields: `source: "quotation:<quote_id>"`, `source_currency`,
    `source_unit_price`, `fx_rate_used`, `fx_source`, `vendor_id`,
    `quote_date`.
  - **Caveat noted in the script header**: these SKUs (e.g.,
    `leo-nature-teak`, `qihome-cherry`) are not in the Leka taxonomy yet.
    Importing to `catalog_pricing` prepopulates the override store but
    the order portal's `/api/order/catalog` won't surface them until
    they're added to `leka-taxonomy.json` (separate follow-up).

### Dry-run results (live FX captured 2026-04-20)

```
FX: 1 USD = 33.04 THB   1 CNY = 4.85 THB   (frankfurter, +3% buffer)

SKU                         Vendor                  Source        THB
leo-nature-teak             leo-nature              27.00 USD     892.01
leo-nature-oak-natural      leo-nature              33.00 USD    1090.23
leo-nature-oak-glacial      leo-nature              36.00 USD    1189.34
qihome-cherry               qihome                 295.00 CNY    1429.48
cn-burmese-teak-a           chinese-teak-vendor    328.00 CNY    1589.39
cn-3layer-teak-locking      chinese-teak-vendor    328.00 CNY    1589.39
cn-multilayer-teak-birch    chinese-teak-vendor    268.00 CNY    1298.65
cn-multilayer-teak-snaplock chinese-teak-vendor    280.00 CNY    1356.80
cn-new-3layer-teak          chinese-teak-vendor    272.00 CNY    1318.03
sentai-stgj68               sentai                   1.74 USD      57.48
```

## [0.8.0] - 2026-04-20

### Added — Production deploy: secrets, IAM, verify script (Phase 6)

Ships the production wiring. After merge the Order Portal is live on
`salesheet.leka.studio` — all six phases working end-to-end.

- **`scripts/setup_order_portal_secrets.sh` (new)** — idempotent
  one-time setup. Creates missing secrets, grants IAM, re-runnable:
  - Auto-generates random `salesheet-flask-session-key` (32-byte hex).
  - Prompts for `firebase-web-api-key` (from Firebase console web-app config).
  - Grants `roles/secretmanager.secretAccessor` to
    `claude@ai-agents-go.iam.gserviceaccount.com` on all new secrets
    plus the existing shared Xero secrets (`xero-client-id`,
    `xero-client-secret`, `xero-tenant-id`, `xero-tokens`).
  - Grants `roles/secretmanager.secretVersionAdder` on `xero-tokens`
    so the refresh flow can write rotated tokens back to the shared secret.
  - Grants project-level `roles/firebase.sdkAdminServiceAgent` +
    `roles/datastore.user`.
  - Prints remaining manual steps: Firebase console providers +
    authorized domains, Slack `/invite @ai_agents` in `#orders-wood-products`.
- **`scripts/verify_order_portal.sh` (new)** — post-deploy smoke suite.
  Confirms:
  - Legacy public routes still 200 (`/`, `/wpc-fence/`, `/wpc-profile/`, `/_healthz`).
  - Auth gate: `/auth/login` renders, `/order/new` + `/admin/orders` → 302,
    `/api/order/catalog` → 401.
  - Legacy `/api/quote` still posts to Slack.
  - Usage: `BASE=http://localhost:8080 scripts/verify_order_portal.sh`
    for local dev; defaults to production URL.
- **`website/salesheet/cloudbuild.yaml`** — final secret + env wiring:
  - Env added: `SLACK_ORDER_CHANNEL`, `FIREBASE_PROJECT_ID`,
    `GCP_PROJECT_ID`, `XERO_TOKENS_SECRET_NAME`, `XERO_DEFAULT_ACCOUNT_CODE`.
  - Secrets added: `FLASK_SECRET_KEY`, `FIREBASE_WEB_API_KEY`,
    `XERO_CLIENT_ID`, `XERO_CLIENT_SECRET`, `XERO_TENANT_ID`,
    `XERO_TOKENS_JSON`.

### Deploy order (for maintainer)
1. `bash scripts/setup_order_portal_secrets.sh` (prompts for Firebase Web API Key).
2. Firebase console: enable Email/Password + Google providers, add
   `salesheet.leka.studio` to Authorized domains.
3. Slack: `/invite @ai_agents` in `#orders-wood-products`.
4. Merge this PR → Cloud Build auto-deploys.
5. `bash scripts/verify_order_portal.sh` to confirm.
6. Sign in at https://salesheet.leka.studio/auth/login with a `@goco.bz`
   account → lands on `/admin/orders`.

### End-to-end flow verified by
1. Sales rep signs in with personal Google → redirected to `/order/new`.
2. Catalog loads with live FX from frankfurter.app. Adds lines via accordion.
3. Customer form fills out, cart autosaves to Firestore every 500 ms.
4. Per-line GM slider enforces 25% floor for external sales.
5. Submit → order number `SO-WD-2026-0001` allocated atomically →
   Xero draft invoice created → Block Kit posted to `#orders-wood-products`.
6. Admin opens the order from the Slack button → confirms → Xero flips
   to AUTHORISED → threaded Slack reply "✅ Confirmed by <admin>".

## [0.7.5] - 2026-04-20

### Added — Admin dashboard (Phase 5)

Full admin UI over submitted + draft orders. List view with filters, detail
view with audit log + action bar, end-to-end state transitions wired to Xero
+ Slack.

- `website/salesheet/order_portal/admin.py` — new routes:
  - `GET  /admin/orders` — filtered list (status, user, date range). Replaces
    the Phase-1 placeholder. Up to 200 most-recent orders.
  - `GET  /admin/orders/<id>` — detail with customer, line items, totals,
    Xero/Slack IDs, and the full `order_events` audit log.
  - `POST /admin/orders/<id>/confirm` — `submitted` → `confirmed`. Updates
    Xero invoice to AUTHORISED. Posts threaded Slack reply "✅ Confirmed by <admin>".
  - `POST /admin/orders/<id>/cancel` — `*` → `cancelled`. Voids Xero invoice.
    Posts threaded Slack reply "❌ Cancelled by <admin>" with optional reason.
  - `POST /admin/orders/<id>/retry-submit` — re-runs the Phase-4 submit for
    orders still in draft with recorded `xero_error` or `slack_error`.
  - `POST /admin/orders/<id>/act-as` — sets `session.impersonating_uid` to
    the order's creator. Subsequent mutations are logged with both
    `actor_uid` (real admin) and `acted_as_uid` in `order_events`.
  - `POST /admin/end-act-as` — clears the impersonation.
- `website/salesheet/order_portal/placeholders.py` — stripped down to a
  single `/admin/` → `/admin/orders` redirect. Admin stubs are gone;
  the real routes take over.
- Templates (reuse `leka.css` tokens):
  - `templates/admin/orders_list.html` — sticky filter bar, pill-status
    column, clickable order numbers, 7-column table.
  - `templates/admin/order_detail.html` — two-column layout: left has
    customer / line items / totals cards, right has audit log.
    Action bar at the top auto-hides buttons that don't apply to the
    current status. Inline JS for `doAction()` that POSTs + reloads.

### Audit trail
Every admin mutation writes an `order_events` doc with `event_type` ∈
{`confirmed`, `cancelled`, `admin_impersonated`, `submit_degraded`, `retry_*`}
plus `actor_uid` (from `g.user`) and `acted_as_uid` (from session). Detail
pages render these in reverse chronological order with pretty-printed JSON.

### Xero error handling
Confirm / cancel wrap the Xero state-change in try/except. On failure, the
Firestore order doc gets `xero_confirm_error` or `xero_cancel_error` fields
written alongside the new status, and the Slack threaded reply includes the
error message. The local status transition still completes so admin isn't
blocked by Xero outages.

## [0.7.4] - 2026-04-20

### Added — Submit flow: Firestore + Xero + Slack (Phase 4)

End-to-end submission for draft orders. `POST /order/<id>/submit` allocates
an order number atomically, creates a Xero draft invoice, posts a Block Kit
card to `#orders-wood-products`, and marks the order submitted. Partial
failures leave the order draft and return HTTP 202 with a degraded flag so
admin can retry.

- `website/salesheet/order_portal/xero_client.py` — lean vendored copy of
  `accounting-automation/integrations/xero/client.py`. Keeps the salesheet
  service independent while sharing the `xero-tokens` Secret Manager secret
  with accounting-automation. Exposes:
  - `is_configured()` — short-circuit check (returns False if client creds missing).
  - `upsert_contact(email, name, company, phone)` — find by email or create.
  - `ensure_item(sku, name)` — auto-create Xero Item if missing.
  - `create_invoice(contact_id, reference, items, tracking_*, status, currency)` —
    ACCREC invoice, 30-day due, optional tracking category.
  - `update_invoice_status(invoice_id, status)` — DRAFT → AUTHORISED / VOIDED.
- `website/salesheet/order_portal/slack_orders.py`:
  - `post_new_order(order, submitter_email, portal_base_url, xero_draft_id)` —
    Block Kit with header, customer/company/email/phone/project fields,
    line count, grand total, context bar showing Xero link, "View order" button.
  - `post_threaded_reply(ts, text)` — plain-text reply for confirm/cancel audits.
  - Channel from `SLACK_ORDER_CHANNEL` env (preferred) or config (`C0AUABRBK41`).
- `website/salesheet/order_portal/order_submit.py` — `POST /order/<id>/submit`:
  1. Re-validates (server-side; never trusts client).
  2. Atomic Firestore transaction on `counters/order_number` →
     `SO-WD-{year}-{seq:04d}` (first order `SO-WD-2026-0001`).
  3. Snapshots `fx_snapshot` ({rate, source, ecb_mid, buffer_pct, fetched_at})
     onto every line item so the order is reconstructable later.
  4. Xero: looks up Contact by email, falls back to the cached
     "Wood Product Customer" id at `counters/xero_fallback_contact_id` if
     the lookup fails; ensure_item for each SKU; create DRAFT invoice
     with tracking category "Leka-Wood-Products".
  5. Slack: posts Block Kit card to `#orders-wood-products`; stores `ts`
     on the order for threaded replies.
  6. Writes `orders/{id}.status = 'submitted'`, `submitted_at`,
     `xero_draft_id`, `slack_message_ts`, `fallback_contact_used`.
  7. Audit event `submitted` (or `submit_degraded` on partial failure).

### Degraded path
If Xero fails, Slack still posts (with "Xero draft pending" in the context).
If Slack fails, the Xero invoice still exists. Either failure keeps the order
in `status=draft` and returns HTTP 202. Admin retry endpoint lands in Phase 5.

### Not yet wired
- Xero secrets (`xero-client-id`, `xero-client-secret`, `xero-tenant-id`,
  `xero-tokens`) come in Phase 6.
- Slack bot must be invited to `#orders-wood-products` via `/invite @ai_agents`.
- Admin confirm (DRAFT → AUTHORISED) and cancel (→ VOIDED) land in Phase 5.

## [0.7.3] - 2026-04-20

### Added — Order builder UI (Phase 3)

Two-column order builder at `/order/<id>` with live catalog on the left and
sticky cart + customer form on the right. Powered by Alpine.js v3, debounced
Firestore autosave (500 ms), and the `/api/order/catalog` endpoint from Phase 2.

- `website/salesheet/order_portal/orders.py` — draft CRUD:
  - `POST /order/new` — creates a `draft-<12-hex>` doc in Firestore `orders/`
    collection, writes `created` audit event, redirects to `/order/<id>`.
  - `GET  /order/<id>` — renders the builder (Jinja).
  - `GET  /order/<id>.json` — JSON payload for client re-hydration on load.
  - `PATCH /order/<id>` — merges partial state; allow-lists customer fields,
    replaces line_items + totals wholesale. Writes `lines_updated` audit event.
  - `POST /order/<id>/validate` — returns `{ok, errors[]}` for the submit gate.
    Validates: customer required fields + email regex + project_type enum,
    at least one line, each line qty > 0 and unit_price > 0 and landed present
    and GM ≥ role floor (25% sales / 0% admin).
  - Access control: admin sees any order, else only own (`created_by_uid` match).
- `website/salesheet/templates/order/detail.html` — two-column Jinja shell
  with Alpine.js `x-data="orderBuilder()"`. Left 60% is an accordion catalog
  (decking open by default, others collapsed). Right 40% sticky column holds
  the customer form, per-line qty steppers, unit-price input + GM slider,
  subtotal/VAT/grand-total, and the submit button gated on `validationErrors`.
- `website/salesheet/static/order/app.js` — `orderBuilder()` Alpine component
  (242 lines). Loads order + catalog + FX in parallel on mount. Debounced
  PATCH autosave. Per-line GM slider refuses below role floor. Add-to-cart
  modal with colour + finish + qty.
- `website/salesheet/static/order/order.css` — order-specific layout; reuses
  all `leka.css` tokens.
- `website/salesheet/order_portal/placeholders.py` — now only holds the
  `/admin/orders` stub; the `/order/new` placeholder is replaced by the real
  route in `orders.py`.
- `website/salesheet/Dockerfile` — `COPY static/order static/order`.

### UX notes
- FX chip in the header shows the live rate + source (frankfurter / cache / fallback).
- Save state indicator next to the draft title: "Draft" → "Saving…" → "Saved ✓".
- SKUs without a resolved landed cost show "Price on request" and a red
  "No landed cost for this SKU yet — ask admin to populate catalog_pricing" line.
- Submit button shows validation errors as a bullet list until everything passes.

## [0.7.2] - 2026-04-20

### Added — Order Portal catalog API with live FX (Phase 2)

Live catalog endpoint for the order builder. Admin-only variant includes
vendor SKU + USD cost; external sales role never sees vendor_code.

- `website/salesheet/order_portal/fx.py` — live FX via **frankfurter.app**
  (ECB mid-market, free, no API key). `fx_buffer_pct` (default 3%) is
  added to approximate a Thai bank's TT Selling spread. 60-min in-memory
  cache. Fallback to `fx_thb_per_usd_fallback` on API error.
- `website/salesheet/order_portal/pricing.py`:
  - `taxonomy()` + `sku_map()` — loaded once, cached via `lru_cache`.
  - `lookup_sku_entry(sku)` — fuzzy match between taxonomy SKUs (e.g.
    `LKP-DK-H-140-23`) and sku-map SKUs (e.g. `LKP-DK-140-23`); strips
    sub-type segment (H/S/G), handles wall-panel `V`→`-HC`, and trailing
    finish suffixes (`-WG`/`-EM`/etc.).
  - `landed_cost_thb_per_m(sku, fx, overrides)` — USD × FX × `landed_multiplier`
    with Firestore `catalog_pricing/{sku}` override precedence.
  - `default_unit_price_thb(sku, landed, overrides)` — landed × `default_markup`.
  - `gm_percent` + `gm_floor_for_role` + `validate_line_gm` — 25% sales floor,
    0% admin floor (admin can override).
- `website/salesheet/order_portal/catalog_api.py`:
  - `GET  /api/order/catalog`     (any authed user) — no vendor_code
  - `GET  /admin/api/catalog`     (admin only)       — includes vendor_code + USD
  - `GET  /api/order/fx`          (any authed user) — current FX snapshot
  - `POST /admin/api/fx/refresh`  (admin only)       — force-refresh FX cache
- Payload is category-grouped (decking, cladding, panels, fence, structure,
  diy-tiles) with per-SKU resolved `colours` (8 palette entries w/ hex +
  grain image), `finishes`, `landed_cost_thb_per_m`, `default_unit_price_thb`.
- DIY-tiles categories expose `diy_palettes` (per-family) instead of the
  full 8-colour palette.

### Changed — Config drift
- `data/catalog/order-portal-config.json` — swapped FX provider from
  Bank of Thailand to **frankfurter.app** + 3% buffer. No API key needed,
  no GCP secret. `fx_rate_type` + `fx_lookback_days` removed; `fx_api_url`
  + `fx_buffer_pct` added. Fallback value unchanged (36.5 THB/USD).
  Decision recorded in the PR description.

### Catalog coverage
Out of 49 taxonomy SKUs, **8 resolve to a USD cost** automatically (all
Premium Co-Ex from PI NS20240516LJ). The remaining 41 (Heritage, Shield,
Structure, DIY) show `landed_cost_thb_per_m: null` until admin populates
`catalog_pricing/{sku}` overrides — implemented in Phase 5.

### Smoke test (live)
Sample: `LKP-DK-H-140-23` — USD 2.55/m × live 33.04 THB/USD × 1.35
= 113.73 THB/m landed → default unit 164.91 THB/m → 31% GM.

## [0.7.1] - 2026-04-20

### Added — Order Portal auth (Phase 1)

Firebase Authentication (Email/Password + Google) wired into the Flask app.
Authenticated routes `/auth/login`, `/auth/session`, `/auth/logout`,
`/auth/me`, plus Phase-1 placeholders for `/order/new` + `/admin/orders`
so the auth flow has working redirect targets. **Microsoft OIDC deferred**
to a later PR once the Azure AD app is provisioned.

- `website/salesheet/order_portal/` — new Flask Blueprint package:
  - `config.py` reads `data/catalog/order-portal-config.json` once at startup
    (lazy-loaded, `lru_cache`); exposes `auth()`, `pricing()`, `slack()`, etc.
  - `firestore_client.py` — singleton for the `products-wood` database using ADC.
  - `auth.py` — Firebase Admin token verify, `@require_auth`, `@require_role`,
    users-collection seeding (`@goco.bz` → admin, else `external_sales`).
  - `placeholders.py` — Phase-1-only stubs for `/order/new` + `/admin/orders`.
- `website/salesheet/templates/` — Jinja2 templates sharing `wpc-profile/css/leka.css`:
  - `layout/base.html` — shared shell with portal nav + user chip + impersonation banner.
  - `auth/login.html` — three providers (Google, Email/Password, Microsoft-disabled);
    uses Firebase JS SDK v10 modular; graceful "config pending" banner when
    `FIREBASE_WEB_API_KEY` secret isn't set yet.
  - `auth/forbidden.html` — 403 page for role mismatch.
- `website/salesheet/server.py` — imports & registers the blueprint **before**
  the static catch-all so `/auth/*`, `/order/*`, `/admin/*` match first.
  Adds `SECRET_KEY` with `os.urandom` fallback + secure cookie config.
- `website/salesheet/requirements.txt` — adds `firebase-admin`,
  `google-cloud-firestore`, `google-cloud-secret-manager`, `requests`.
- `website/salesheet/Dockerfile` — copies `order_portal/`, `templates/`, and
  `data/catalog/` into the image. The latter is staged by a new cloudbuild
  pre-step that copies the repo-root config into the build context.
- `website/salesheet/cloudbuild.yaml` — new `stage-config` step; adds
  `FIREBASE_PROJECT_ID` + `GCP_PROJECT_ID` + `SLACK_ORDER_CHANNEL` env vars.
  **No new secrets referenced yet** — `salesheet-flask-session-key` +
  `firebase-web-api-key` come in Phase 6 to avoid breaking the deploy
  before those secrets exist.

### Graceful degradation
- Login page renders with a yellow banner when `FIREBASE_WEB_API_KEY` is unset.
- Session cookie uses `os.urandom` fallback when `FLASK_SECRET_KEY` missing
  (ephemeral — changes every pod start, but the public site still works).
- Legacy routes (`/wpc-fence/`, `/wpc-profile/`, `/catalog/`, `/api/quote`,
  `/api/render-scene`, `/_healthz`) completely unchanged.

### Manual setup required (before Phase 6 merge)
1. Firebase console → link to project `ai-agents-go` → enable Email/Password + Google providers.
2. Auth → Authorized domains → add `salesheet.leka.studio`.
3. IAM grant on `claude@ai-agents-go.iam.gserviceaccount.com`:
   - `roles/firebase.sdkAdminServiceAgent`
   - `roles/datastore.user` on Firestore `products-wood`.

## [0.7.0] - 2026-04-20

### Added — Order Portal config (Phase 0)

Frozen single source of truth for the upcoming internal order portal (routes `/auth/*`, `/order/*`, `/admin/*`). No code changes yet — this PR only locks the config so subsequent phases can't drift.

- **`data/catalog/order-portal-config.json` (new, v1.0.0)** — canonical values for:
  - Order-number format `SO-WD-{year}-{seq:04d}` (first order: `SO-WD-2026-0001`).
  - Slack channel `#orders-wood-products` (`C0AUABRBK41`).
  - Xero fallback contact "Wood Product Customer", tracking category "Leka-Wood-Products", DRAFT → AUTHORISED → VOIDED flow.
  - Auth: Email/Password + Google only for Phase 1 (Microsoft OIDC deferred). `@goco.bz` → admin; others → external_sales.
  - Pricing formula: `landed_cost_thb_per_m = sku_map.line_m_price_usd × BoT_FX × 1.35`, default unit price = landed × 1.45, GM floor 25% for sales / 0% for admin, VAT 7%.
  - FX provider: Bank of Thailand TT Selling rate, 60 min cache, 5-day lookback for weekends/holidays, fallback 36.5 THB/USD if `BOT_API_CLIENT_ID` secret is unset or the API errors.
  - Firestore database `products-wood`, Cloud Run service `salesheet-leka` in `asia-southeast1`.
- **No runtime dependency on the file yet.** Phase 2 (`/api/order/catalog`) will be the first consumer.
- Legacy routes (`/wpc-fence/`, `/wpc-profile/`, `/catalog/`, `/api/quote`, `/api/render-scene`) explicitly listed as untouchable.

## [0.6.1] - 2026-04-19

### Changed — Gemini 3 Pro Image Preview cleanup pass

- All 60 taxonomy-referenced catalog images (46 product photos + 8 Leka colour grain swatches + 4 texture grid cards + 2 additional) reprocessed through `gemini-3-pro-image-preview`.
- Input: the v0.6.0 PIL-extracted crops.
- Output: 1024×1024 studio-quality product photos — pure white seamless background, soft natural shadow, product centred, no text / labels / grid lines / adjacent-row bleed.
- `scripts/gemini_clean_images.py` — reusable processor. Pulls `gemini-api-key` from GCP Secret Manager, rate-limits at 2.5 s between calls, retries on transient failures, supports `--overwrite` or `_clean.jpg` suffix output, `--filter` / `--limit` / `--skip` args for selective re-runs.

## [0.6.0] - 2026-04-19

### Changed — Image review pass (PIL-only, superseded by v0.6.1)

- PDFs re-extracted at 220 DPI (was 150) for higher source resolution (`scripts/extract_pdf_pages.py`).
- Co-Ex product crops: tighter x-bounds (115..350) exclude row# column AND vendor-code column; conservative 28px y-pads prevent neighbor-row bleed.
- Heritage crops: new x-bounds (150..400) exclude the wider first-generation row# column; row height recalibrated to 310px at 220 DPI; 35px y-pads.
- ASA crops: exclude Chinese title text ("XXX*YY格栅") by starting at y=185 per half; exclude the right-side cross-section drawing + spec text by cutting x at 50% page width; custom bbox with minimal upward padding.

### Added — Inline SVG cross-sections per product card

- `cross_section_svg()` in `scripts/generate_wpc_profile_pages.py` renders a scaled cross-section SVG sized to the product's real width × thickness.
- Profile geometry varies by sub-category: hollow / grooved (6-hole circles) / fluted (rib teeth) / solid (plain rectangle).
- Cap shield stripes drawn on Signature (LKP) and Shield (LKA) series. Embossed grain hints drawn on Heritage (LKH) 3D variants.
- Dimension annotations (W mm, T mm) rendered in the series accent colour.
- Cross-section sits between the photo and the spec/palette body on each card — brings back the technical consolidated preview from v0.4.0 /catalog/.

## [0.5.0] - 2026-04-19

### Added — /wpc-profile/ multi-page catalog (replaces single-page /catalog/)

- **Main landing page** `website/salesheet/wpc-profile/index.html` — hero + 6 category cards (Decking, Cladding, Panels, Fence, Structure, DIY Tiles) with thumbnails, SKU counts and sub-category counts. Series legend introduces 5 engineered lines.
- **6 category sub-pages** with sub-category tab filters:
  - `wpc-profile/decking/` — 14 SKUs across Signature Hollow, Signature Solid, Shield Deckway, Heritage Hollow, Heritage Grooved.
  - `wpc-profile/cladding/` — 7 SKUs across Signature Flat, Shield Flat, Shield Grille, Heritage Flat.
  - `wpc-profile/panels/` — 12 SKUs across Signature Fluted, Half-Covered, Shield Grille, Heritage Fluted.
  - `wpc-profile/structure/` — 9 SKUs across Columns, Beams, Joists, Edging.
  - `wpc-profile/diy-tiles/` — 4 tile families (WPC Co-Ex / PP Plastic / Grass / Stone) with per-family palettes.
  - `wpc-profile/colours/` — full 8-colour library (large swatches with real wood-grain photos) + 4-texture reference grid.
- **New engineered line:** Shield Series (`LKA-` prefix) — ASA triple-capped profiles extracted from the AOLO ASA catalog. 12 new SKUs across grilles, wall panels, deckway, fence and edging.
- **Real manufacturer photography:** 239 product photos, ASA hero shots, DIY tile closeups, Heritage strip photos and wood-grain colour swatches cropped from 4 vendor PDF catalogs (Jackson Co-Ex, First-Gen, DIY, ASA — 72 source pages totalling ~250 MB). All vendor branding and factory codes stripped via tight pixel crops. Output under `website/salesheet/wpc-profile/images/{grain,products,asa,diy,heritage}/`.
- **Shared design system stylesheet:** `website/salesheet/wpc-profile/css/leka.css` — single source of truth, pulled by every sub-page. Eliminates the 400-line inline `<style>` block duplication from v0.4.0.
- **Taxonomy data model:** `data/catalog/leka-taxonomy.json` — 5 series, 8 colours, 4 textures, 6 categories, 18 sub-categories, 46 products. Drives the page generator — single edit updates every page on `python scripts/generate_wpc_profile_pages.py`.
- **Generator scripts:**
  - `scripts/extract_pdf_pages.py` — uses PyMuPDF to rasterise vendor PDFs into `.claude/pdf-pages/*.png`.
  - `scripts/crop_catalog_images.py` — Pillow-based cropper. Colour-card cells, product-photo cells (leftmost table column), ASA hero quadrants, DIY hero blocks, Heritage leftmost strip.
  - `scripts/generate_wpc_profile_pages.py` — renders all 7 pages from the taxonomy JSON. Idempotent.
- **Preview dev server entry** `"wpc-profile-site"` added to `.claude/launch.json` on port 8085.

### Changed

- `website/salesheet/Dockerfile` — adds `COPY wpc-profile static/wpc-profile` so Cloud Run serves the new routes. Existing `/catalog/` copy retained as a legacy redirect.
- `website/salesheet/index.html` — landing-page link updated from `/catalog/` → `/wpc-profile/` (the broader library).

### Verified

- All 7 pages return `200 OK`.
- All 64 image/CSS asset references resolve (manual curl sweep across every page).
- Static server proven via local Python `http.server`.

### Notes for next session

- Domain: existing live host is `salesheet.leka.studio`. User request mentions `salesheet.lekastudio.com` — likely a typo for the existing `leka.studio` domain; left the deployment pointing at the current Cloud Run service. Confirm before any DNS change.
- First-Generation catalog extraction yielded 130 heritage strip photos — only 7 wired into products so far. Remaining 120+ available for future Heritage SKU expansion.

## [0.4.3] - 2026-04-19

### Added
- `website/salesheet/catalog/index.html` — complete Leka-branded WPC profiles catalog at `/catalog/`. Covers all 16 core WPC profiles across 4 categories (decking, cladding, wide wall panels, fence) in 2 engineered lines (Signature Co-Ex / Heritage Solid WPC). Each product card renders an inline SVG technical cross-section scaled to actual dimensions, 3-up spec panel (width × thickness × length), surface finish chips, and the full 8-colour swatch palette. Includes tab-filter per category (All / Signature / Heritage), colour palette section mirroring `/wpc-fence/images/swatches/`, four-finish gallery (Brushed / 3D Embossed / Knife-Cut / Stipple) and a 12-tile "250+ extended catalog on request" summary.
- `data/catalog/leka-sku-map.json` — internal-only mapping of every Leka SKU (e.g. `LKP-DK-140-23`) to the underlying vendor code and source PI. Documents the SKU scheme (`LK[P|H]-[TYPE]-[WIDTH]-[THICKNESS][-VARIANT]`), 10 product types, 4 variant suffixes, all 16 priced products, and the unpriced extended-catalog counts. Not served to the public — reference only for sales & procurement.
- New route `/catalog/` — wired into `website/salesheet/Dockerfile` (`COPY catalog static/catalog`) so the Flask static server exposes it on Cloud Run under `salesheet.leka.studio/catalog/`.

### Note
- Originally landed on branch as v0.4.0 at commit d81a21a, renumbered to 0.4.3 during the branch/main merge since main had its own 0.4.0–0.4.2 stream for fence configurator work.

### Changed
- `website/salesheet/index.html` — landing page now links both `/catalog/` (complete profile library) and `/wpc-fence/` (fence-specific sales sheet) so customers land on either the broad catalog or the configurator-led fence flow.

## [0.4.2] - 2026-04-19

### Changed
- `website/salesheet/wpc-fence/configurator/index.html` — three SVG preview refinements:
  - Boards now stack from the **bottom up**. The first (bottom-most) board sits flush against the top of the bottom rail — no gap beneath it. Any remainder space (when the fence height isn't a perfect multiple of board-plus-gap) appears at the top under the top rail, matching how a real field-installed fence is built.
  - Replaced the pixel-per-mm `scale` variable with a natural millimetre `viewBox`. The SVG is drawn in real-world mm coordinates and the viewBox matches the fence's actual proportions, so the preview scales responsively via CSS rather than an internal multiplier.
  - Zoomed in: tighter margins around the assembly (was ~90 px padding scaled; now 100 mm side / 180 mm top / 320 mm bottom in viewBox units) so the fence fills the preview area. The wrapper uses `height: clamp(320px, 46vh, 460px)` with the SVG at 100% × 100% and `preserveAspectRatio="xMidYMid meet"` for clean contain-scaling across viewport sizes.

## [0.4.1] - 2026-04-19

### Changed
- `website/salesheet/wpc-fence/images/swatches/lk-0n.jpg` — all 8 swatches rotated 90° so the woodgrain runs horizontally (704×399 landscape). Fixes both the SVG plank fill (grain now runs along the length of each horizontal plank) and the reference image sent to Gemini.
- `website/salesheet/server.py` — `_build_render_prompt` adds an explicit "grain MUST run horizontally along the length of each plank, embossed grain must be clearly visible" directive, so Gemini preserves the woodgrain in the final render rather than smoothing it out.
- `website/salesheet/wpc-fence/configurator/index.html` — right-panel layout swap:
  - Old "Your configuration" summary card replaced by an interactive `config-panel` containing all controls (Series / Bay / Height / Gap / Fence run / Gates), a compact totals band (Total length + Bays / Posts / Boards), and the Request-a-quote button.
  - Left column simplified to preview (SVG + swatch picker) + scene render only. The colour picker still lives beside the SVG preview; the right-panel header shows a mini-chip of the currently-selected colour.

## [0.4.0] - 2026-04-19

### Changed
- `website/salesheet/server.py` — `/api/render-scene` now generates scenes with a consistent directorial template ("Variant C / Lifestyle In-Use") and explicit 16:9 landscape aspect ratio:
  - Replaced the free-form scene description map with a structured `_SCENES` dict holding a `context` clause + a scene-appropriate `people` clause per scene (residential family, hospitality couple, hospital nurse + patient, school students, resort family).
  - `_build_render_prompt` now emits a single disciplined template: 50 mm / f/2.8, pedestrian 3/4 vantage, 1.5 m camera height, bright softened afternoon light, medium-shallow DoF, editorial-lifestyle colour grading.
  - `_call_gemini_image` now passes `generationConfig.imageConfig.aspectRatio: "16:9"` so Gemini returns landscape 1344×768 PNGs instead of portrait defaults.
- `website/salesheet/wpc-fence/configurator/index.html` — render-result container aspect ratio updated from `3/2` to `16/9` to match the new output.

## [0.3.1] - 2026-04-19

### Changed
- `website/salesheet/wpc-fence/configurator/index.html` — three UX refinements from live-review feedback:
  - Gap between boards: replaced the range slider with a +/− stepper (0–15 cm, 1 cm steps) for consistent feel with the other controls.
  - SVG preview: replaced the tiled `<pattern>` fill with one `<image preserveAspectRatio="slice"/>` per board so the woodgrain no longer produces spurious vertical seams where the pattern used to repeat.
  - Colour picker moved out of the controls stack into a side-by-side split with the live SVG preview; swatch chips enlarged (72 px) and each now shows both the `LK-nn` code and the colour name (e.g. "LK-05 / Teak").

## [0.3.0] - 2026-04-18

### Added
- `website/salesheet/wpc-fence/configurator/index.html` — interactive WPC fence configurator. Real-time SVG side-elevation preview driven by series, bay width (1.5 / 1.8 / 2.0 / 2.9 m), height (1.5 / 2.0 / 2.5 / 3.0 m), board gap slider (0–15 cm covering privacy at 0 and slatted/louvered at 1–15), fence run input, single/double gate steppers, and 8-swatch colour picker. Sticky summary panel computes bays, posts, total boards, and total length with gates added in.
- `POST /api/render-scene` endpoint in `website/salesheet/server.py` — calls Gemini 2.5 Flash Image ("Nanobanana") via the REST API to render the configured spec into a chosen scene (residential / hospitality / hospital / school / resort). Includes SHA-256 spec caching, per-IP rate limit (20 s), and a daily budget guard (`RENDER_DAILY_BUDGET`, default 200).
- New Cloud Run secret binding `GEMINI_API_KEY=gemini-api-key:latest` and env var `GEMINI_IMAGE_MODEL` in `website/salesheet/cloudbuild.yaml`. Requires the GCP Secret Manager secret `gemini-api-key` to be created from `Credentials Claude Code/gemini-api-key.txt` before deploy.

### Changed
- `website/salesheet/wpc-fence/index.html` — new hero CTA "Configure your fence ▶" linking to `/wpc-fence/configurator/`, plus a matching CTA under the Configurations section. Applications section expanded from 3 cards (Residential / Hospitality / Commercial) to 5 cards (Residential / Hospitality / Hospital / School / Resort) to mirror the configurator's scene choices.
- `website/salesheet/server.py` — extended `/api/quote` `ALLOWED_FIELDS` with `bayWidth`, `boardGap`, `fenceRun`, `singleGates`, `doubleGates`, `totalLength`, `sceneImageUrl`. `_post_to_slack` Slack lead block now includes bay width, board gap, gate breakdown (single × double), and the configurator-generated scene render as an image block when provided.

## [0.2.0] - 2026-04-18

### Changed
- `website/salesheet/wpc-fence/index.html` — responsive overhaul. Replaced the 2-breakpoint system (960px, 560px) with 6 breakpoints (1024 / 860 / 640 / 480 / 360) plus `max-height: 600px` (landscape phones) and `prefers-reduced-motion`. Fixes tablet-portrait grid collapse gap, adds tighter gutters and full-width CTAs on phones, makes the quote modal full-bleed on small phones, bleeds the comparison table to screen edges under 480px, and scales section padding / hero height across devices.

## [0.1.0] - 2026-03-24

### Added
- Initial project template with CI/CD pipeline
- CLAUDE.md session protocol
- cloudbuild.yaml for GCP Cloud Build
- verify.sh post-build verification script
- Dockerfile for Cloud Run deployment
- setup.sh bootstrap script
- manifest.example.json credentials template
- PR template with AI eval score fields
- Deployment Plan and Build Plan templates
