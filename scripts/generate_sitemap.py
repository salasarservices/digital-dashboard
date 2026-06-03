from __future__ import annotations

import argparse
import os
import sys
import time

# Allow running from project root: python scripts/generate_sitemap.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sitemap.builder import build
from sitemap.cache import append_run_log, load_cache, save_cache
from sitemap.clients import build_gsc_client
from sitemap.crawler import crawl
from sitemap.gsc_enricher import enrich

_SC_SITE_URL = "https://www.salasarservices.com/"


def _load_sa_json() -> str:
    sa = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "")
    if sa:
        return sa
    secrets_path = os.path.join(os.path.dirname(__file__), "..", ".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        try:
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore[no-redef]
            with open(secrets_path, "rb") as fh:
                secrets = tomllib.load(fh)
            return secrets.get("gcp", {}).get("service_account", "")
        except Exception as exc:
            print(f"[warn] Could not read secrets.toml: {exc}", file=sys.stderr)
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate sitemap.xml for salasarservices.com")
    parser.add_argument("--force",    action="store_true", help="Re-crawl all pages, ignore cache")
    parser.add_argument("--dry-run",  action="store_true", help="Print stats only, no files written")
    parser.add_argument("--output",   default="output",    help="Output directory (default: ./output)")
    parser.add_argument("--no-gsc",   action="store_true", help="Skip GSC enrichment")
    parser.add_argument("--verbose",  action="store_true", help="Log each URL as processed")
    args = parser.parse_args()

    cache_path = os.path.join(args.output, "sitemap_cache.json")
    runs_path  = os.path.join(args.output, "sitemap_runs.jsonl")

    t0 = time.time()
    status = "success"
    error_msg = ""
    pages: list = []

    try:
        cache = load_cache(cache_path)
        print(f"[crawl] Starting crawl (force={args.force})…")
        pages, excluded = crawl(cache=cache, force=args.force, verbose=args.verbose)
        print(f"[crawl] {len(pages)} indexable URLs, {len(excluded)} excluded.")

        if not args.no_gsc:
            sa_json = _load_sa_json()
            if not sa_json:
                print("[warn] No GCP service account found — skipping GSC enrichment.", file=sys.stderr)
            else:
                print("[gsc]  Enriching with GSC impressions…")
                sc = build_gsc_client(sa_json)
                pages = enrich(pages, sc, _SC_SITE_URL)
        else:
            for p in pages:
                p.setdefault("priority", 0.5)
                p.setdefault("changefreq", "monthly")

        if args.dry_run:
            print(f"\n[dry-run] Would write {len(pages)} URLs to {args.output}/sitemap.xml")
            for p in pages[:5]:
                print(f"  {p['url']}  priority={p.get('priority', 0.5)}  imgs={len(p.get('images', []))}")
            if len(pages) > 5:
                print(f"  … and {len(pages) - 5} more.")
            return 0

        sitemap_path, _ = build(pages, args.output)
        save_cache(cache, cache_path)

        image_count = sum(len(p.get("images", [])) for p in pages)
        duration = time.time() - t0
        print(f"[done] {sitemap_path}  ({len(pages)} URLs, {image_count} images, {duration:.1f}s)")

    except Exception as exc:
        status = "failed"
        error_msg = str(exc)
        print(f"[fatal] {exc}", file=sys.stderr)
        return 2

    duration = time.time() - t0
    image_count = sum(len(p.get("images", [])) for p in pages)
    append_run_log(
        {
            "url_count":        len(pages),
            "image_count":      image_count,
            "duration_seconds": round(duration, 1),
            "status":           status,
            "error_msg":        error_msg,
            "output_path":      os.path.abspath(os.path.join(args.output, "sitemap.xml")),
            "triggered_by":     "cli",
        },
        runs_path,
    )
    return 0 if status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
