from __future__ import annotations

import os
import time

import streamlit as st

st.set_page_config(page_title="Sitemap Generator | Salasar", layout="wide", page_icon="🗺️")

# ── Login gate — must come immediately after set_page_config ──────────────────
if not st.session_state.get("logged_in"):
    st.error("🔒 Access denied. Please log in from the **Dashboard** page first.")
    st.stop()

from sitemap.builder import build  # noqa: E402 — intentionally after login gate
from sitemap.cache import (  # noqa: E402
    append_run_log,
    load_cache,
    load_run_log,
    save_cache,
)
from sitemap.clients import build_gsc_client  # noqa: E402
from sitemap.crawler import crawl  # noqa: E402
from sitemap.gsc_enricher import enrich  # noqa: E402

_CACHE_PATH  = "output/sitemap_cache.json"
_RUNS_PATH   = "output/sitemap_runs.jsonl"
_OUTPUT_DIR  = "output"
_SC_SITE_URL = "https://www.salasarservices.com/"


@st.cache_resource(ttl=3600)
def _get_gsc_client() -> object:
    return build_gsc_client(st.secrets["gcp"]["service_account"])


def _status_badge(status: str) -> str:
    colours = {"success": "#16a34a", "partial": "#d97706", "failed": "#dc2626"}
    colour = colours.get(status, "#64748b")
    return (
        f"<span style='background:{colour};color:#fff;padding:2px 10px;"
        f"border-radius:12px;font-size:.78em;font-weight:700'>{status.upper()}</span>"
    )


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("## 🗺️ Sitemap Generator")
st.caption(
    "Crawls salasarservices.com · enriches with live GSC impressions · "
    "outputs a standards-compliant sitemap.xml with image captions."
)

# ── Last run stats ────────────────────────────────────────────────────────────
runs = load_run_log(_RUNS_PATH)
if runs:
    last = runs[-1]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Last run",  last.get("run_at", "—")[:10])
    c2.metric("URLs",      last.get("url_count", "—"))
    c3.metric("Images",    last.get("image_count", "—"))
    c4.metric("Duration",  f"{last.get('duration_seconds', 0):.0f}s")
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
                           help="Faster run — priorities default to 0.5.")

# ── Generate ──────────────────────────────────────────────────────────────────
if generate:
    t0 = time.time()
    status = "success"
    error_msg = ""
    pages: list = []

    progress_bar = st.progress(0)
    status_ph    = st.empty()

    try:
        # ── 1. Load cache ────────────────────────────────────────────────────
        status_ph.info("📂 Loading crawl cache…")
        cache = load_cache(_CACHE_PATH)

        # ── 2. Crawl ─────────────────────────────────────────────────────────
        status_ph.info("🌐 Seeding URL list from existing sitemap.xml…")
        progress_bar.progress(2)

        def _on_crawl(done: int, in_queue: int, excl: int) -> None:
            total_seen = done + in_queue or 1
            pct = max(3, min(38, int(done / total_seen * 38)))
            progress_bar.progress(pct)
            status_ph.markdown(
                f"🔍 **Crawling…** &nbsp;"
                f"<code>{done}</code> crawled &nbsp;·&nbsp; "
                f"<code>{in_queue}</code> in queue &nbsp;·&nbsp; "
                f"<code>{excl}</code> excluded",
                unsafe_allow_html=True,
            )

        pages, excluded_pages = crawl(cache=cache, force=force, on_progress=_on_crawl)
        progress_bar.progress(40)
        status_ph.success(
            f"✅ Crawl complete — **{len(pages)}** indexable URLs · "
            f"**{len(excluded_pages)}** excluded"
        )

        # ── 3. GSC enrichment ─────────────────────────────────────────────────
        if not skip_gsc:
            status_ph.info("📊 Fetching GSC impressions (single API call)…")
            progress_bar.progress(42)

            def _on_gsc(done: int, total: int) -> None:
                pct = 42 + int(done / max(total, 1) * 31)   # 42 → 73 %
                progress_bar.progress(pct)
                status_ph.markdown(
                    f"📊 **GSC enrichment…** &nbsp;"
                    f"<code>{done} / {total}</code> URLs assigned priority",
                    unsafe_allow_html=True,
                )

            sc = _get_gsc_client()
            pages = enrich(pages, sc, _SC_SITE_URL, on_progress=_on_gsc)
            progress_bar.progress(75)
            status_ph.success("✅ GSC enrichment complete — real priorities assigned.")
        else:
            for p in pages:
                p.setdefault("priority",        0.5)
                p.setdefault("changefreq",       "monthly")
                p.setdefault("gsc_impressions",  0)
                p.setdefault("gsc_clicks",       0)
                p.setdefault("gsc_position",     None)

        # ── 4. Build XML ─────────────────────────────────────────────────────
        status_ph.info("🔨 Assembling sitemap.xml…")
        progress_bar.progress(78)
        sitemap_path, _ = build(pages, _OUTPUT_DIR)
        progress_bar.progress(90)

        # ── 5. Save cache ────────────────────────────────────────────────────
        status_ph.info("💾 Saving crawl cache…")
        save_cache(cache, _CACHE_PATH)
        progress_bar.progress(100)

        duration    = time.time() - t0
        image_count = sum(len(p.get("images", [])) for p in pages)
        status_ph.success(
            f"🎉 **Done in {duration:.1f}s** — "
            f"**{len(pages)}** URLs · **{image_count}** images · "
            f"sitemap.xml ready to download."
        )

    except Exception as exc:
        status = "failed"
        error_msg = str(exc)
        progress_bar.progress(0)
        status_ph.error(f"❌ Generation failed: {exc}")

    duration    = time.time() - t0
    image_count = sum(len(p.get("images", [])) for p in pages)

    append_run_log(
        {
            "url_count":        len(pages),
            "image_count":      image_count,
            "duration_seconds": round(duration, 1),
            "status":           status,
            "error_msg":        error_msg,
            "output_path":      (
                os.path.abspath(os.path.join(_OUTPUT_DIR, "sitemap.xml"))
                if status != "failed" else ""
            ),
            "triggered_by": "streamlit",
        },
        _RUNS_PATH,
    )

# ── Download button ───────────────────────────────────────────────────────────
sitemap_file = os.path.join(_OUTPUT_DIR, "sitemap.xml")
if os.path.exists(sitemap_file):
    with open(sitemap_file, "rb") as fh:
        st.download_button(
            "⬇️  Download sitemap.xml",
            data=fh,
            file_name="sitemap.xml",
            mime="application/xml",
        )

st.divider()

# ── URL table from cache ───────────────────────────────────────────────────────
cache = load_cache(_CACHE_PATH)
if cache:
    import pandas as pd

    rows      = []
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
        st.dataframe(df, use_container_width=True, height=420)

    if excl_rows:
        with st.expander(f"🚫 Excluded URLs ({len(excl_rows)})"):
            st.dataframe(pd.DataFrame(excl_rows), use_container_width=True)
