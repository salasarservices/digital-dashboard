from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import streamlit as st

from sitemap.builder import build
from sitemap.cache import (
    append_run_log,
    load_cache,
    load_run_log,
    save_cache,
)
from sitemap.clients import build_gsc_client
from sitemap.crawler import crawl
from sitemap.gsc_enricher import enrich

_CACHE_PATH   = "output/sitemap_cache.json"
_RUNS_PATH    = "output/sitemap_runs.jsonl"
_OUTPUT_DIR   = "output"
_SC_SITE_URL  = "https://www.salasarservices.com/"

st.set_page_config(page_title="Sitemap Generator | Salasar", layout="wide", page_icon="🗺️")


@st.cache_resource(ttl=3600)
def _get_gsc_client():
    return build_gsc_client(st.secrets["gcp"]["service_account"])


def _status_badge(status: str) -> str:
    colours = {"success": "#16a34a", "partial": "#d97706", "failed": "#dc2626"}
    colour = colours.get(status, "#64748b")
    return (
        f"<span style='background:{colour};color:#fff;padding:2px 10px;"
        f"border-radius:12px;font-size:.78em;font-weight:700'>{status.upper()}</span>"
    )


st.markdown("## 🗺️ Sitemap Generator")
st.caption("Crawl salasarservices.com, enrich with GSC impressions, and output a standards-compliant sitemap.xml.")

# ── Last run stats ────────────────────────────────────────────────────────────
runs = load_run_log(_RUNS_PATH)
if runs:
    last = runs[-1]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Last run", last.get("run_at", "—")[:10])
    c2.metric("URLs", last.get("url_count", "—"))
    c3.metric("Images", last.get("image_count", "—"))
    c4.metric("Duration", f"{last.get('duration_seconds', 0):.0f}s")
    with c5:
        st.markdown("**Status**")
        st.markdown(_status_badge(last.get("status", "unknown")), unsafe_allow_html=True)
else:
    st.info("No runs yet. Click **Generate Sitemap** to run for the first time.")

st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────
col_btn, col_force, col_gsc = st.columns([2, 1, 1])
with col_btn:
    generate = st.button("🚀 Generate Sitemap", type="primary", use_container_width=True)
with col_force:
    force = st.checkbox("Force re-crawl", value=False,
                        help="Ignore the 7-day cache and re-crawl every URL.")
with col_gsc:
    skip_gsc = st.checkbox("Skip GSC enrichment", value=False,
                           help="Useful for a quick crawl without API quota usage.")

# ── Generate ──────────────────────────────────────────────────────────────────
if generate:
    t0 = time.time()
    status = "success"
    error_msg = ""

    with st.spinner("Loading crawl cache…"):
        cache = load_cache(_CACHE_PATH)

    progress = st.progress(0, text="Starting crawl…")
    try:
        with st.spinner("Crawling site…"):
            pages, excluded = crawl(cache=cache, force=force)
        progress.progress(40, text=f"Crawled {len(pages)} pages, {len(excluded)} excluded.")

        if not skip_gsc:
            with st.spinner("Enriching with GSC data…"):
                sc = _get_gsc_client()
                pages = enrich(pages, sc, _SC_SITE_URL)
            progress.progress(75, text="GSC enrichment complete.")
        else:
            for p in pages:
                p.setdefault("priority", 0.5)
                p.setdefault("changefreq", "monthly")
                p.setdefault("gsc_impressions", 0)
                p.setdefault("gsc_clicks", 0)
                p.setdefault("gsc_position", None)

        with st.spinner("Building XML…"):
            sitemap_path, _ = build(pages, _OUTPUT_DIR)
        progress.progress(90, text="XML written.")

        save_cache(cache, _CACHE_PATH)
        progress.progress(100, text="Done.")

    except Exception as exc:
        status = "failed"
        error_msg = str(exc)
        st.error(f"Generation failed: {exc}")

    duration = time.time() - t0
    image_count = sum(len(p.get("images", [])) for p in pages) if status != "failed" else 0

    append_run_log(
        {
            "url_count":        len(pages) if status != "failed" else 0,
            "image_count":      image_count,
            "duration_seconds": round(duration, 1),
            "status":           status,
            "error_msg":        error_msg,
            "output_path":      os.path.abspath(sitemap_path) if status != "failed" else "",
            "triggered_by":     "streamlit",
        },
        _RUNS_PATH,
    )

    if status == "success":
        st.success(f"Done in {duration:.1f}s — {len(pages)} URLs, {image_count} images.")

# ── Download button ───────────────────────────────────────────────────────────
sitemap_file = os.path.join(_OUTPUT_DIR, "sitemap.xml")
if os.path.exists(sitemap_file):
    with open(sitemap_file, "rb") as fh:
        st.download_button(
            "⬇️ Download sitemap.xml",
            data=fh,
            file_name="sitemap.xml",
            mime="application/xml",
        )

st.divider()

# ── URL table ─────────────────────────────────────────────────────────────────
cache = load_cache(_CACHE_PATH)
if cache:
    import pandas as pd

    rows = []
    excl_rows = []
    for url, rec in cache.items():
        if rec.get("excluded"):
            excl_rows.append({"url": url, "reason": rec.get("exclusion_reason", "")})
        else:
            rows.append({
                "url":             url,
                "priority":        rec.get("priority", 0.5),
                "changefreq":      rec.get("changefreq", "monthly"),
                "image_count":     len(rec.get("images", [])),
                "gsc_impressions": rec.get("gsc_impressions", 0),
                "http_status":     rec.get("http_status", 0),
            })

    if rows:
        st.markdown("### Crawled URLs")
        df = pd.DataFrame(rows).sort_values("priority", ascending=False)
        st.dataframe(df, use_container_width=True, height=400)

    if excl_rows:
        with st.expander(f"Excluded URLs ({len(excl_rows)})"):
            st.dataframe(pd.DataFrame(excl_rows), use_container_width=True)
