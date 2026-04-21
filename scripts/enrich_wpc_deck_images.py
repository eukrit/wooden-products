"""Enrich and centre the /wpc-deck/ sales-sheet images with Gemini
`gemini-3-pro-image-preview`.

Two prompt variants:
  - PRODUCT_CARD  — the 2 range-card product shots, isolated on seamless
                    light background, centred, soft shadow, 1024×1024.
  - CONTEXT_SCENE — hero, gallery and configuration shots: preserve the
                    scene (pool / terrace / rooftop context) but tighten
                    composition, recentre, upscale, and clean any odd
                    artefacts. 1600×1000-ish landscape or 1024×1024 square.

Output defaults to `_enriched.jpg` next to each source; --overwrite
replaces the original.

Env:
  GEMINI_API_KEY — falls back to GCP Secret Manager secret `gemini-api-key`.

Usage:
  python scripts/enrich_wpc_deck_images.py              # dry run
  python scripts/enrich_wpc_deck_images.py --go
  python scripts/enrich_wpc_deck_images.py --go --overwrite
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "website" / "salesheet" / "wpc-deck" / "images"

MODEL = "gemini-3-pro-image-preview"
ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{MODEL}:generateContent"
)

PROMPT_PRODUCT_CARD = (
    "Enrich this wood-plastic composite (WPC) deck board product photo for "
    "a premium architecture catalogue. Keep the board's shape, colour, "
    "woodgrain texture, profile edges and any visible clip or groove "
    "detail faithful to the source. Remove any residual text, stickers, "
    "manufacturer marks, measurement annotations, row numbers, grid "
    "lines, or neighbouring objects. Centre the board cleanly in the "
    "frame on a clean light surface with a very soft natural shadow, a "
    "subtle warm studio light and a seamless neutral background (pale "
    "cream or soft white). Output a sharp, crisp, high-detail 1024×1024 "
    "square product photo suitable for a Leka Studio sales sheet."
)

PROMPT_CONTEXT_SCENE = (
    "Enrich this architectural scene photograph of a wood-plastic "
    "composite (WPC) outdoor deck installation for a premium "
    "architecture catalogue. Preserve the setting — residential terrace, "
    "pool surround, rooftop, hotel or restaurant context — and keep the "
    "decking material, surrounding architecture, planting and natural "
    "daylight mood faithful to the source. Tighten the composition so "
    "the decking surface reads as the clear subject. Recentre, level the "
    "horizon, and crop or extend the edges naturally where needed. Lift "
    "shadow detail slightly, warm the daylight, and remove any small "
    "distractions (stray rubbish, random people in the background, "
    "watermarks, captions, logos, cables). Do not stylise — keep it "
    "photorealistic. Output a sharp, crisp, high-detail 1024×1024 square "
    "photo suitable for a Leka Studio sales sheet gallery."
)

# Map each source image to a prompt variant.
TARGETS = {
    # Product range cards — isolated on light background
    "deck-premium-card.jpg":        PROMPT_PRODUCT_CARD,
    "deck-classic-card.jpg":        PROMPT_PRODUCT_CARD,
    # Hero / context scenes — preserve scene, tighten composition
    "deck-premium-hero.jpg":        PROMPT_CONTEXT_SCENE,
    "deck-config-residential.jpg":  PROMPT_CONTEXT_SCENE,
    "deck-config-hospitality.jpg":  PROMPT_CONTEXT_SCENE,
    "deck-config-commercial.jpg":   PROMPT_CONTEXT_SCENE,
    "gallery-residential.jpg":      PROMPT_CONTEXT_SCENE,
    "gallery-hospitality.jpg":      PROMPT_CONTEXT_SCENE,
    "gallery-commercial.jpg":       PROMPT_CONTEXT_SCENE,
}


def get_api_key() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return os.environ["GEMINI_API_KEY"].strip()
    env = dict(os.environ)
    env.setdefault("CLOUDSDK_PYTHON", sys.executable)
    gcloud = shutil.which("gcloud") or (
        r"C:\Users\Eukrit\AppData\Local\Google\Cloud SDK"
        r"\google-cloud-sdk\bin\gcloud.cmd"
    )
    r = subprocess.run(
        [gcloud, "secrets", "versions", "access", "latest",
         "--secret=gemini-api-key", "--project=ai-agents-go"],
        env=env, capture_output=True, text=True, shell=False,
    )
    if r.returncode != 0:
        raise SystemExit(f"Failed to fetch gemini-api-key: {r.stderr}")
    return r.stdout.strip()


def call_gemini(image_path: Path, prompt: str, api_key: str,
                retries: int = 2) -> bytes | None:
    img_b64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    ext = image_path.suffix.lower().lstrip(".")
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg",
            "png": "image/png"}.get(ext, "image/jpeg")

    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inlineData": {"mimeType": mime, "data": img_b64}},
            ]
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "temperature": 0.35,
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
            with urllib.request.urlopen(req, timeout=120) as r:
                body = json.loads(r.read())
            parts = body["candidates"][0]["content"]["parts"]
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
            return None
        except urllib.error.HTTPError as exc:
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
    ap.add_argument("--go",        action="store_true",
                    help="actually run (default: dry)")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace originals instead of writing _enriched.jpg")
    ap.add_argument("--filter",    type=str, default="",
                    help="substring filter on filename")
    ap.add_argument("--rate",      type=float, default=2.5,
                    help="min seconds between API calls")
    args = ap.parse_args()

    items = []
    for name, prompt in TARGETS.items():
        if args.filter and args.filter not in name:
            continue
        p = IMG_DIR / name
        if not p.is_file():
            print(f"  MISSING: {p}")
            continue
        items.append((p, prompt))

    print(f"Images to process: {len(items)}")
    for p, pr in items:
        kind = "product-card" if pr is PROMPT_PRODUCT_CARD else "context-scene"
        print(f"  {p.relative_to(ROOT)}  [{kind}]")
    if not args.go:
        print("\n(dry run — pass --go to execute)")
        return 0

    api_key = get_api_key()
    print("Got API key. Starting processing...\n")

    ok = fail = 0
    last_call = 0.0
    for i, (p, prompt) in enumerate(items, start=1):
        rel = p.relative_to(ROOT)
        kind = "product" if prompt is PROMPT_PRODUCT_CARD else "scene"
        print(f"[{i}/{len(items)}] {rel}  [{kind}]")
        wait = args.rate - (time.time() - last_call)
        if wait > 0:
            time.sleep(wait)
        last_call = time.time()

        png = call_gemini(p, prompt, api_key)
        if not png:
            print("  -> FAILED")
            fail += 1
            continue

        out = p if args.overwrite else p.with_name(p.stem + "_enriched.jpg")
        out.write_bytes(png)
        print(f"  -> {out.relative_to(ROOT)} ({len(png)//1024} KB)")
        ok += 1

    print(f"\nDone. ok={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
