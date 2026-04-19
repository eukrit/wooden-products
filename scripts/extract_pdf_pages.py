"""Extract PNG pages from vendor catalog PDFs.

Usage: python scripts/extract_pdf_pages.py

Reads from data/raw/slack/ … writes to .claude/pdf-pages/.
Filenames: <prefix>_p<N>.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # pymupdf

ROOT = Path(__file__).resolve().parents[1]
OUT  = ROOT / ".claude" / "pdf-pages"
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = [
    # (pdf_path, prefix) - resolve ASA filename via directory glob to avoid Unicode literal issues
    (r"C:\Users\Eukrit\OneDrive\Documents\Claude Code\2026 Wood Products Claude\data\raw\slack\vendor-anhui-aolo-wpc\DIY CATALOG(1).pdf", "diy"),
    (r"C:\Users\Eukrit\OneDrive\Documents\Claude Code\2026 Wood Products Claude\data\raw\slack\supplier-flooring-and-decking\First generation catalog from Jackson 250801.pdf", "firstgen"),
    (r"C:\Users\Eukrit\OneDrive\Documents\Claude Code\2026 Wood Products Claude\data\raw\slack\supplier-flooring-and-decking\Co-extrusion products catalog from Jackson.pdf", "jackson_ce"),
]
# Append AOLO ASA by glob so Chinese chars in filename don't require manual escaping
_asa = list(Path(r"C:\Users\Eukrit\OneDrive\Documents\Claude Code\2026 Wood Products Claude\data\raw\slack\vendor-anhui-aolo-wpc").glob("*ASA*.pdf"))
if _asa:
    SOURCES.append((str(_asa[0]), "aolo_asa"))

DPI = 220

for pdf_path, prefix in SOURCES:
    p = Path(pdf_path)
    if not p.is_file():
        print(f"SKIP (missing): {p.name}")
        continue
    doc = fitz.open(p)
    safe_name = p.name.encode("ascii", "replace").decode("ascii")
    print(f"-> {safe_name} - {len(doc)} pages")
    for i, page in enumerate(doc, start=1):
        mat = fitz.Matrix(DPI / 72.0, DPI / 72.0)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        out = OUT / f"{prefix}_p{i}.png"
        pix.save(out)
    doc.close()

print(f"\nDone. Output: {OUT}")
print(f"Total PNGs: {len(list(OUT.glob('*.png')))}")
