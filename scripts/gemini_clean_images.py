"""Clean up Leka product catalog images using Gemini 3 Pro Image Preview.

For each image referenced from data/catalog/leka-taxonomy.json, send it to the
gemini-3-pro-image-preview model with a cleanup instruction:
  - remove residual text / labels / grid lines
  - recenter the product
  - isolate on white background
  - upscale to ~1024px longest edge

Writes cleaned outputs alongside the originals, with `_clean.jpg` suffix.
After review, swap image paths in the taxonomy or overwrite originals.

Env:
  GEMINI_API_KEY — loaded from GCP Secret Manager "gemini-api-key"

Usage:
  python scripts/gemini_clean_images.py              # dry run — lists what would run
  python scripts/gemini_clean_images.py --go         # run it
  python scripts/gemini_clean_images.py --go --limit 3   # test with 3 images first
  python scripts/gemini_clean_images.py --go --overwrite # replace originals
"""
from __future__ import annotations
import argparse
import base64
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAX = ROOT / "data" / "catalog" / "leka-taxonomy.json"
IMG_ROOT = ROOT / "website" / "salesheet"

MODEL = "gemini-3-pro-image-preview"
ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"

PROMPT = (
    "Clean up this product catalog photograph of a wood-plastic composite (WPC) "
    "extrusion profile. Keep the product itself unchanged in shape, colour, "
    "material character and woodgrain texture. Remove any overlaid text, "
    "labels, measurement annotations, grid lines, table borders, row numbers, "
    "or fragments of neighbouring products. Centre the main product in the "
    "frame. Place it on a clean pure-white seamless background with a very "
    "soft natural shadow below. Output a professional studio-quality product "
    "photo, sharp, crisp, high-detail, 1024 × 1024 pixels."
)


def get_api_key() -> str:
    """Fetch from GCP Secret Manager. Falls back to GEMINI_API_KEY env var."""
    import os
    import shutil
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    env = dict(os.environ)
    env.setdefault("CLOUDSDK_PYTHON", sys.executable)
    gcloud = shutil.which("gcloud") or r"C:\Users\Eukrit\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    r = subprocess.run(
        [gcloud, "secrets", "versions", "access", "latest",
         "--secret=gemini-api-key", "--project=ai-agents-go"],
        env=env, capture_output=True, text=True, shell=False,
    )
    if r.returncode != 0:
        raise SystemExit(f"Failed to fetch gemini-api-key: {r.stderr}")
    return r.stdout.strip()


def collect_used_images() -> list[Path]:
    """Return absolute paths of images referenced from taxonomy JSON."""
    data = json.loads(TAX.read_text(encoding="utf-8"))
    paths: list[Path] = []
    for cat in data.get("categories", {}).values():
        for p in cat.get("products", []):
            img = p.get("image")
            if img and img.startswith("/wpc-profile/"):
                paths.append(IMG_ROOT / img.lstrip("/"))
    # Also include the 8 colour grain swatches used in palette strip
    for c in data.get("palette_full", []):
        g = c.get("grain_image")
        if g and g.startswith("/wpc-profile/"):
            paths.append(IMG_ROOT / g.lstrip("/"))
    # And the grid texture cards
    for t in data.get("textures", []):
        g = t.get("grid_image")
        if g and g.startswith("/wpc-profile/"):
            paths.append(IMG_ROOT / g.lstrip("/"))
    # Dedupe, preserve order
    seen = set()
    out = []
    for p in paths:
        if p not in seen and p.is_file():
            seen.add(p)
            out.append(p)
    return out


def call_gemini(image_path: Path, api_key: str, retries: int = 2) -> bytes | None:
    img_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    # Detect mime
    ext = image_path.suffix.lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext, "image/jpeg")

    payload = {
        "contents": [{
            "parts": [
                {"text": PROMPT},
                {"inlineData": {"mimeType": mime, "data": img_b64}},
            ]
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "temperature": 0.4,
        },
    }
    url = ENDPOINT + "?key=" + urllib.parse.quote(api_key)

    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as r:
                body = json.loads(r.read())
            parts = body["candidates"][0]["content"]["parts"]
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
            return None
        except urllib.error.HTTPError as exc:
            err = ""
            try:
                err = exc.read().decode("utf-8", errors="replace")[:400]
            except Exception:
                err = str(exc)
            print(f"  HTTP {exc.code}: {err[:200]}")
            if exc.code in (400, 403, 404):
                return None
            if attempt < retries:
                time.sleep(4 * (attempt + 1))
                continue
            return None
        except urllib.error.URLError as exc:
            print(f"  network: {exc}")
            if attempt < retries:
                time.sleep(4 * (attempt + 1))
                continue
            return None
        except (KeyError, IndexError, ValueError) as exc:
            print(f"  parse: {exc!r}")
            return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--go",        action="store_true", help="actually run (default: dry)")
    ap.add_argument("--overwrite", action="store_true", help="replace originals instead of writing _clean.jpg")
    ap.add_argument("--limit",     type=int, default=0, help="process only N images")
    ap.add_argument("--skip",      type=int, default=0, help="skip first N images")
    ap.add_argument("--filter",    type=str, default="", help="substring filter — only images containing this")
    ap.add_argument("--rate",      type=float, default=1.5, help="min seconds between API calls")
    args = ap.parse_args()

    targets = collect_used_images()
    if args.filter:
        targets = [p for p in targets if args.filter in str(p)]
    if args.skip:
        targets = targets[args.skip:]
    if args.limit:
        targets = targets[:args.limit]

    print(f"Images to process: {len(targets)}")
    if not args.go:
        for p in targets[:20]:
            print(f"  {p.relative_to(ROOT)}")
        if len(targets) > 20:
            print(f"  ... and {len(targets) - 20} more")
        print("\n(dry run — pass --go to execute)")
        return 0

    api_key = get_api_key()
    print("Got API key. Starting processing...\n")

    ok = 0
    fail = 0
    last_call = 0.0
    for i, p in enumerate(targets, start=1):
        rel = p.relative_to(ROOT)
        print(f"[{i}/{len(targets)}] {rel}")
        # Rate limit
        wait = args.rate - (time.time() - last_call)
        if wait > 0:
            time.sleep(wait)
        last_call = time.time()

        png = call_gemini(p, api_key)
        if not png:
            print("  -> FAILED")
            fail += 1
            continue

        if args.overwrite:
            out = p
        else:
            out = p.with_name(p.stem + "_clean.jpg")
        out.write_bytes(png)
        print(f"  -> {out.relative_to(ROOT)} ({len(png)//1024} KB)")
        ok += 1

    print(f"\nDone. ok={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
