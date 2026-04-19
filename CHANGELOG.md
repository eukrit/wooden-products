# Changelog

All notable changes to this project will be documented in this file.

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

## [0.4.0] - 2026-04-19

### Added
- `website/salesheet/catalog/index.html` — complete Leka-branded WPC profiles catalog at `/catalog/`. Covers all 16 core WPC profiles across 4 categories (decking, cladding, wide wall panels, fence) in 2 engineered lines (Signature Co-Ex / Heritage Solid WPC). Each product card renders an inline SVG technical cross-section scaled to actual dimensions, 3-up spec panel (width × thickness × length), surface finish chips, and the full 8-colour swatch palette. Includes tab-filter per category (All / Signature / Heritage), colour palette section mirroring `/wpc-fence/images/swatches/`, four-finish gallery (Brushed / 3D Embossed / Knife-Cut / Stipple) and a 12-tile "250+ extended catalog on request" summary.
- `data/catalog/leka-sku-map.json` — internal-only mapping of every Leka SKU (e.g. `LKP-DK-140-23`) to the underlying vendor code and source PI. Documents the SKU scheme (`LK[P|H]-[TYPE]-[WIDTH]-[THICKNESS][-VARIANT]`), 10 product types, 4 variant suffixes, all 16 priced products, and the unpriced extended-catalog counts. Not served to the public — reference only for sales & procurement.
- New route `/catalog/` — wired into `website/salesheet/Dockerfile` (`COPY catalog static/catalog`) so the Flask static server exposes it on Cloud Run under `salesheet.leka.studio/catalog/`.

### Changed
- `website/salesheet/index.html` — landing page now links both `/catalog/` (complete profile library) and `/wpc-fence/` (fence-specific sales sheet) so customers land on either the broad catalog or the configurator-led fence flow.

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
