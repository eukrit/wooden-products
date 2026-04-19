# Changelog

All notable changes to this project will be documented in this file.

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
