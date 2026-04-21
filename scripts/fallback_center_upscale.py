"""PIL fallback: centre-crop / letter-box + upscale to 1024×1024.

Used for wpc-deck images that Gemini Image Preview couldn't enrich (503
capacity errors). Produces a clean, centred, 1024×1024 result so the
sales sheet never shows the raw source asset. Result is clearly inferior
to a Gemini enrichment — when capacity returns, re-run the Gemini
script in --overwrite mode to replace these with studio-quality output.

Usage:
  python scripts/fallback_center_upscale.py file1 file2 …
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageFilter

TARGET = 1024


def process(path: Path) -> None:
    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size

        # Scale up so the shorter edge reaches TARGET, then centre-crop the
        # longer edge. If the source is already ≥ TARGET on one side, just
        # centre-crop.
        if w < TARGET or h < TARGET:
            scale = TARGET / min(w, h)
            im = im.resize((round(w * scale), round(h * scale)),
                           Image.LANCZOS)
            w, h = im.size

        # Centre-crop to square TARGET × TARGET
        left = (w - TARGET) // 2
        top = (h - TARGET) // 2
        im = im.crop((left, top, left + TARGET, top + TARGET))

        # Light sharpening to compensate for any upscale blur
        im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=80, threshold=2))

        im.save(path, format="JPEG", quality=92, optimize=True,
                progressive=True)
        print(f"  {path.name}: {TARGET}×{TARGET}, {path.stat().st_size // 1024} KB")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: fallback_center_upscale.py <jpg> [<jpg> ...]")
        return 2
    for arg in sys.argv[1:]:
        process(Path(arg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
