from __future__ import annotations

"""
Audit image alt text using Google Gemini Vision.

Reads output/sitemap_cache.json, classifies every image as:
  manual         — exact match in CAPTION_MAP (already reviewed, skip)
  folder_fallback — folder known but page not in CAPTION_MAP
  unknown        — folder detection returned 'unknown'

Sends non-manual images to Gemini 1.5 Flash and writes a side-by-side
comparison CSV: current_caption vs ai_caption.

Usage:
  python scripts/audit_alt_text.py --dry-run          # preview, no API calls
  python scripts/audit_alt_text.py --limit 50         # first 50 fallback images
  python scripts/audit_alt_text.py --all-images       # entire site
  python scripts/audit_alt_text.py --mode unknown-only # strictest filter
"""

import argparse
import csv
import io
import json
import os
import sys
import time
from typing import Any
from urllib.parse import urlparse

import requests
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sitemap.cache import load_cache
from sitemap.captioner import CAPTION_MAP, detect_folder, generate_caption

_DEFAULT_CACHE  = "output/sitemap_cache.json"
_DEFAULT_OUTPUT = "output/alt_text_audit.csv"
_GEMINI_MODEL   = "gemini-1.5-flash"
_RATE_SLEEP     = 0.5   # seconds between API calls
_COST_PER_IMAGE = 0.0001  # USD approximate (Gemini 1.5 Flash, low-res image)

_PROMPT = """\
You are writing SEO-optimised alt text for an insurance broker website \
called Salasar Services (India, pan-India insurance brokerage).

Context:
- Page: {page_url}
- Image category folder: {folder}

Rules:
1. Describe what is literally visible in the image
2. Relate it naturally to the page context (insurance / service / industry shown)
3. End with "| Salasar Services"
4. Maximum 120 characters total
5. Never begin with "Image of", "Photo of", or "Picture of"
6. Never mention competitor brands
7. If the image is purely decorative (background texture, divider, icon with \
no informational content) return exactly the word: DECORATIVE

Return ONLY the alt text string or the word DECORATIVE — no explanation, \
no quotes, no markdown.\
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_gemini_api_key() -> str:
    """Read Gemini API key from .streamlit/secrets.toml or GEMINI_API_KEY env var."""
    secrets_path = os.path.join(
        os.path.dirname(__file__), "..", ".streamlit", "secrets.toml"
    )
    if os.path.exists(secrets_path):
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore[no-redef]
            with open(secrets_path, "rb") as fh:
                secrets = tomllib.load(fh)
            return secrets.get("gemini", {}).get("api_key", "")
        except Exception as exc:
            print(f"[warn] Could not read secrets.toml: {exc}", file=sys.stderr)
    return os.environ.get("GEMINI_API_KEY", "")


def _build_gemini_model(api_key: str) -> object:
    """Build a Gemini GenerativeModel using an API key."""
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(_GEMINI_MODEL)


def _classify(img_url: str, page_path: str) -> str:
    """Return 'manual', 'folder_fallback', or 'unknown'."""
    folder = detect_folder(img_url)
    if folder == "unknown":
        return "unknown"
    if folder in CAPTION_MAP.get(page_path, {}):
        return "manual"
    return "folder_fallback"


def _download_image(url: str) -> Image.Image | None:
    try:
        resp = requests.get(
            url,
            timeout=12,
            headers={"User-Agent": "SalasarAltTextAudit/1.0"},
        )
        if resp.status_code != 200:
            return None
        return Image.open(io.BytesIO(resp.content))
    except Exception:
        return None


def _ai_caption(model: object, img_url: str, page_path: str, folder: str) -> str:
    """Send image to Gemini and return generated alt text."""
    img = _download_image(img_url)
    if img is None:
        return "DOWNLOAD_FAILED"
    prompt = _PROMPT.format(
        page_url=f"https://www.salasarservices.com{page_path}",
        folder=folder,
    )
    try:
        response = model.generate_content([img, prompt])  # type: ignore[union-attr]
        text = response.text.strip()
        if text != "DECORATIVE" and len(text) > 120:
            text = text[:117] + "…"
        return text
    except Exception as exc:
        return f"API_ERROR: {exc}"


def _collect(
    cache: dict[str, Any],
    mode: str,
) -> list[dict[str, str]]:
    """Build the list of image candidates to audit."""
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()

    for page_url, rec in cache.items():
        if rec.get("excluded") or rec.get("http_status", 0) >= 400:
            continue
        page_path = urlparse(page_url).path.rstrip("/") or "/"

        for img in rec.get("images", []):
            src = img.get("src", "").strip()
            if not src or src in seen:
                continue
            seen.add(src)

            classification = _classify(src, page_path)

            if mode == "unknown-only" and classification != "unknown":
                continue
            if mode == "fallback" and classification == "manual":
                continue
            # mode == "all" keeps everything

            candidates.append({
                "page_url":       page_url,
                "page_path":      page_path,
                "image_url":      src,
                "folder":         detect_folder(src),
                "caption_type":   classification,
                "current_caption": generate_caption(src, page_path),
            })

    return candidates


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit image alt text with Gemini Vision and write a review CSV."
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Max images to audit (default: 50). Ignored if --all-images is set.",
    )
    parser.add_argument(
        "--all-images", action="store_true",
        help="Audit every candidate image — overrides --limit.",
    )
    parser.add_argument(
        "--mode", choices=["fallback", "unknown-only", "all"], default="fallback",
        help=(
            "fallback (default): folder_fallback + unknown images only. "
            "unknown-only: only images with unrecognised folder. "
            "all: include manually-mapped images too."
        ),
    )
    parser.add_argument("--cache",  default=_DEFAULT_CACHE,  help="Sitemap cache JSON")
    parser.add_argument("--output", default=_DEFAULT_OUTPUT, help="Output CSV path")
    parser.add_argument("--no-confirm", action="store_true", help="Skip y/N prompt")
    parser.add_argument("--dry-run",    action="store_true", help="Preview only, no API calls")
    parser.add_argument("--verbose",    action="store_true", help="Print each image URL")
    args = parser.parse_args()

    # ── Load cache ────────────────────────────────────────────────────────────
    cache = load_cache(args.cache)
    if not cache:
        print(
            f"[error] Cache empty or not found at '{args.cache}'.\n"
            "Run 'python scripts/generate_sitemap.py' first.",
            file=sys.stderr,
        )
        return 2

    # ── Collect candidates ────────────────────────────────────────────────────
    all_candidates = _collect(cache, args.mode)
    candidates = all_candidates if args.all_images else all_candidates[: args.limit]

    if not candidates:
        print("[info] No images match the current filter. Try --mode all.")
        return 0

    type_counts: dict[str, int] = {}
    for c in candidates:
        type_counts[c["caption_type"]] = type_counts.get(c["caption_type"], 0) + 1

    est_cost = len(candidates) * _COST_PER_IMAGE

    print(f"\n{'═'*62}")
    print(f"  🔍  Alt Text Audit  —  Gemini 1.5 Flash")
    print(f"{'═'*62}")
    print(f"  Cache            {args.cache}")
    print(f"  Mode             {args.mode}")
    print(f"  Total candidates {len(all_candidates)}")
    print(f"  Will audit       {len(candidates)}")
    for t, n in sorted(type_counts.items()):
        print(f"    {t:<22} {n}")
    print(f"  Est. cost        ~${est_cost:.4f} USD  (~₹{est_cost * 84:.2f})")
    print(f"  Output           {args.output}")
    print(f"{'═'*62}\n")

    if args.dry_run:
        print("[dry-run] First 10 candidates:\n")
        for c in candidates[:10]:
            print(f"  [{c['caption_type']:<16}] {c['image_url'][:72]}")
            print(f"    Current → {c['current_caption'][:80]}")
        return 0

    if not args.no_confirm:
        ans = input(
            f"  Proceed with {len(candidates)} Gemini API calls "
            f"(~${est_cost:.4f})? [y/N] "
        ).strip().lower()
        if ans != "y":
            print("  Aborted.")
            return 0

    # ── Build Gemini client ───────────────────────────────────────────────────
    api_key = _load_gemini_api_key()
    if not api_key:
        print(
            "[error] No Gemini API key found.\n"
            "Ensure .streamlit/secrets.toml has a [gemini] api_key entry\n"
            "or set the GEMINI_API_KEY environment variable.",
            file=sys.stderr,
        )
        return 2

    print("[init] Authenticating with Gemini…")
    try:
        model = _build_gemini_model(api_key)
    except Exception as exc:
        print(f"[error] Could not build Gemini client: {exc}", file=sys.stderr)
        return 2
    print("[init] Ready.\n")

    # ── Process images ────────────────────────────────────────────────────────
    results: list[dict[str, Any]] = []
    errors = 0

    for i, c in enumerate(candidates, 1):
        if args.verbose:
            print(f"  [{i:3d}/{len(candidates)}] {c['image_url'][:70]}")
        elif i % 10 == 0:
            print(f"  {i}/{len(candidates)} processed…")

        caption = _ai_caption(model, c["image_url"], c["page_path"], c["folder"])
        is_error = caption.startswith(("DOWNLOAD_FAILED", "API_ERROR"))
        if is_error:
            errors += 1

        results.append({
            "page_url":        c["page_url"],
            "image_url":       c["image_url"],
            "folder":          c["folder"],
            "caption_type":    c["caption_type"],
            "current_caption": c["current_caption"],
            "ai_caption":      caption,
            "char_count":      len(caption) if not is_error else 0,
            "approved":        "",   # ← human fills Y / N
            "promote_to_map":  "",   # ← human fills Y to bake into CAPTION_MAP
        })

        time.sleep(_RATE_SLEEP)

    # ── Write CSV ─────────────────────────────────────────────────────────────
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    fieldnames = [
        "page_url", "image_url", "folder", "caption_type",
        "current_caption", "ai_caption", "char_count",
        "approved", "promote_to_map",
    ]
    with open(args.output, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n{'═'*62}")
    print(f"  ✅  Done.")
    print(f"  Processed   {len(results)}")
    print(f"  Errors      {errors}")
    print(f"  Output      {os.path.abspath(args.output)}")
    print(f"{'═'*62}")
    print(
        "\n  Next steps:"
        "\n  1. Open the CSV in Excel"
        "\n  2. Review 'ai_caption' vs 'current_caption'"
        "\n  3. Mark 'approved' = Y for captions you want to keep"
        "\n  4. Mark 'promote_to_map' = Y to permanently add to CAPTION_MAP"
        "\n  5. Share the reviewed CSV and I'll update captioner.py automatically\n"
    )

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
