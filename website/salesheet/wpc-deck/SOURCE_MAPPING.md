# Internal SKU Mapping — wpc-deck

**Confidential. Do not surface vendor identities or codes on the public sales sheet.**

Every public Leka SKU in `wpc-deck/index.html` maps to a specific upstream
supplier SKU. Use this table when converting a customer quote into a
purchase order — the price, lead time, MOQ, and warranty pass-through all
attach to the upstream code, not the Leka-facing one.

| Leka public SKU   | Leka marketing name               | Upstream source               | Upstream SKU | Upstream dimension | Notes |
|-------------------|-----------------------------------|-------------------------------|--------------|--------------------|-------|
| LKD-P-140         | Premium Deck Board 140 × 20       | Maxis Products Co., Ltd.      | DECK-140     | 20 × 140 mm        | Made-to-order, MOQ 300 m or 50 m² per colour. Cutting lengths 1.0 – 5.8 m. |
| LKD-C-097         | Classic Deck Board 97 × 20        | Maxis Products Co., Ltd.      | Deck-002     | 20 × 97 mm         | Made-to-order, MOQ 300 m or 50 m² per colour. Cutting lengths 1.0 – 5.8 m. |

## Upstream source reference

- Page scraped: https://www.maxiswood.com/MAXIS%20DECK/667395af094fe70013e56355/langEN
- Scrape date: 2026-04-21 (see `data/parsed/maxiswood/maxiswood_catalog.json` at repo root, category slug `maxis-deck`)
- Upstream-stated warranty: **3 years** (surface). Upstream has no stated
  structural warranty. The longer structural figures published on the Leka
  sales sheet reflect the expected service life of the HDPE-polymer core
  under normal use and are offered on a **pass-through** basis — always
  subject to the manufacturer's published limited warranty current at
  time of delivery (see §Warranty disclaimer in the sales sheet).

## Colour mapping

Maxis publishes a 9-colour palette. The Leka sales sheet standardises on
the house 8-colour palette (LK-01 … LK-08). The 9th Maxis colour is
dropped; specific colour-to-colour mapping is approved on a project basis
at sample review, not from catalogue names.

## Warranty pass-through

Per Leka sales-sheet policy (warranty guardrails, §8 of
`website/salesheet/README.md`):

- Published **surface** warranty matches manufacturer (3 yr Classic, bumped
  to 5 yr on Premium contingent on applying the specified anti-UV top coat
  at install).
- Published **structural** warranty (15 yr Premium, 10 yr Classic) is
  Leka's underwritten pass-through figure reflecting the HDPE-polymer core
  lifespan and is enforceable only under the disclaimer block printed in
  the sales sheet — i.e. written claim within 60 days, board-replacement-
  or-material-credit remedy, no labour / consequential, subject to
  manufacturer's published terms.
- Anti-UV top coat is sold as an add-on. If the customer declines it, the
  surface warranty is reduced to manufacturer-bare (3 yr on both series)
  and this must be noted on the order.

## Minimum order (per colour, per SKU)

- 300 linear metres, OR
- 50 m² of finished deck, whichever is reached first.
- Custom colour surcharge: THB 25,000 per production lot (quoted at
  sample confirmation).

## Lead time

- 4 – 6 weeks from confirmed PO + colour sample sign-off.
- Anti-UV coating adds ~1 week.
