# Handoff: WeChat → wooden-products — WOODEN FLOORING ingestion

_Prepared 2026-06-08 by the `wechat-automation` session that mined the source data._

## What this is
The `wechat-automation` repo's Firestore DB (`wechat-documents`) was searched for documents
and suppliers related to **real wooden flooring**. This package hands off the cleaned result
so it can be **stored and parsed into this project's `products-wood` database**.

**Scope = genuine wood flooring ONLY.** Explicitly EXCLUDED at the user's request:
SPC, WPC, vinyl/LVT/LVP, laminate, PVC, "artificial wood", composite, rubber/epoxy/sports
flooring, and wood-look porcelain/ceramic floor *tiles*.

## The data file
`data/incoming/wechat_wooden_flooring_export.json` — contains:
- `products` (**55 confirmed** wooden-flooring records, from WeChat catalog extraction)
- `needs_review` (**25 records** — all classified as "Floor Tile", almost certainly wood-look
  porcelain/ceramic = artificial. Two have wood names: `TEAKWOOD CHEVRON SATIN`,
  `ROSEWOOD RUSSET`. Verify against the Hongyu catalog PDF before deciding; default = exclude.)
- `source_files` (7 source documents that produced the products, **with GCS paths**)
- `extra_flooring_files` (1 extra: `2026-01-07 Kihome Floors.pdf` — Kihome flooring doc with
  no extracted products yet; worth parsing)
- `vendors` (rollup grouped by vendor)

## Source location (read-only — copy assets FROM here)
- Source Firestore: **`wechat-documents`** (project `ai-agents-go`, `asia-southeast1`)
- Source GCS bucket: **`gs://wechat-documents-attachments`** (all `gcs_path` values point here)
- All 8 source files were verified present in GCS on 2026-06-08.

## The 4 confirmed wooden-flooring vendors
| WeChat vendor | Products | Source file (GCS) | Maps to `products-wood` vendor |
|---|---|---|---|
| **Qihao Home Kihome** | 24 Oak engineered flooring (series 9090/8116/8086/8106/9051/9108) | `document/2025-11/英文.pdf` + `document/2026-01/2026-01-07 Kihome Floors.pdf` | **EXISTING vendor `qihome`** ("Qihome Cherry Engineered Wood Flooring", CN, `engineered_flooring`). Merge into it — do NOT create a duplicate. Add aliases "Qihao Home", "Kihome". |
| **Bimei** (必美地板) | 23 Italian-style engineered oak/walnut parquet (Rovere / Noce Americano; collection names Padova, Bardolino, Treviso, Asolo, Segreti…) | `catalog/2026-04/必美地板意大利菲列德罗画册（拼花）.pdf` | NEW vendor `bimei` (CN manufacturer/importer, `engineered_flooring`, subcategory parquet/herringbone). |
| **(unattributed) ENGINEERED CATALOG** | 7 engineered Oak planks (Oak Terra/Mountain/Charcoal/Chalk Washed/Nordic/Maroon/Montana) | `catalog/2026-01/2026-01-07 ENGINEERED CATALOG.pdf` | Identify the brand from the PDF cover. May belong to an existing vendor (e.g. `leo-nature`, `qihome`) or be NEW. Parse the PDF to attribute. |
| **Visconti** (GIORIO visconti / 卓越卡萨) | 1 three-layer solid/engineered wood flooring (三层实木地板) | `document/2026-02/2026-02-11 ...GIORIO visconti Profile.pdf` | NEW vendor `visconti` (Italian, company profile — flooring is one of several product lines). |

## Target (this project)
- Firestore DB: **`products-wood`** (`ai-agents-go`, `asia-southeast1`)
- Collections: `vendors`, `products`, `quotations`, `product_images`, `categories`
- Schema reference: `scripts/firestore/schema.py`
- Asset bucket: **`gs://products-wood-assets`** (organize by vendor folder, e.g. `bimei/`, `qihome/`, `visconti/`)
- Existing upload helpers: `scripts/firestore/upload_data.py`, `upload_pdf_data.py`, `upload_images.py`
- Relevant categories already seeded: `engineered_flooring`, `timber_flooring` (use these).

## Suggested steps
1. Read `wechat_wooden_flooring_export.json`. The WeChat extraction is **sparse** (often no
   dimensions/price/finish). Treat it as the index of *what exists*, not the final record.
2. For richer specs, **pull the source PDFs from `gs://wechat-documents-attachments`** (paths in
   the file) and parse them (PDF table/vision extraction) — especially the Bimei parquet catalog,
   the ENGINEERED CATALOG, and `英文.pdf`/`Kihome Floors.pdf`. Mine: collection/series name,
   wood species, dimensions (LxWxT mm), construction (solid / 3-layer / multi-layer / engineered),
   finish, grade, pattern (plank/herringbone/chevron/parquet), price + currency, MOQ.
3. Map to the `products` schema. Use `category` = `engineered_flooring` (or `timber_flooring` for
   solid). Set `source` = `"wechat-automation:wechat-documents"` and keep the WeChat
   `product_id`/`source_file_id` in `notes` for traceability.
4. **Dedupe vendors**: merge Qihao Home Kihome into existing `qihome`. Cross-check Bimei/Visconti
   against existing vendors before creating.
5. Copy each source PDF into `gs://products-wood-assets/<vendor>/` and create `product_images`
   metadata records (`type: catalog` / `quotation_scan` / `datasheet`).
6. Resolve the `needs_review` tiles (parse Hongyu catalog) — exclude if porcelain/ceramic.
7. Follow this project's Claude Process Standards: TodoWrite, update `CHANGELOG.md` +
   `docs/build-summary.html`, regenerate hub, run `verify.sh`, then commit & push (the user
   should confirm before pushing per this project's safety rules — it is NOT auto-commit opted-in).

## Notes / gotchas
- `Nature Green Floors` appeared in the raw search but was dropped — its file is an **SPC**
  quotation (out of scope).
- Many `vendor`-level aggregates in WeChat mix wood + WPC/SPC lines (e.g. Qihao also sells WPC).
  Only the **wood** SKUs are in `products` here; do not import the WPC/SPC siblings.
- Console encoding on this Windows box is cp1252 — set `PYTHONIOENCODING=utf-8` before any
  script that prints CJK/Thai.
