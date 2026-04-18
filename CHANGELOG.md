# Changelog

All notable changes to this project will be documented in this file.

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
