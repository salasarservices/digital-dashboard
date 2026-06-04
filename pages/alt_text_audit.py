from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Alt Text Audit | Salasar", layout="wide", page_icon="🤖")

# ── Login gate ────────────────────────────────────────────────────────────────
if not st.session_state.get("logged_in"):
    st.error("🔒 Access denied. Please log in from the **Dashboard** page first.")
    st.stop()

from sitemap.cache import load_cache  # noqa: E402
from sitemap.captioner import CAPTION_MAP, detect_folder, generate_caption  # noqa: E402

_CACHE_PATH    = "output/sitemap_cache.json"
_CLAUDE_MODEL  = "claude-haiku-4-5"
_RATE_SLEEP    = 0.3

_PROMPT = """\
You are writing SEO-optimised alt text for an insurance broker website \
called Salasar Services (India, pan-India insurance brokerage).

Context:
- Page: {page_url}
- Image category: {folder}

Rules:
1. Describe what is literally visible in the image
2. Relate it naturally to the page context (insurance / service / industry)
3. End with "| Salasar Services"
4. Maximum 120 characters total
5. Never begin with "Image of", "Photo of", or "Picture of"
6. Never mention competitor brands
7. If the image is purely decorative (background texture, divider, icon with \
no informational content) return exactly: DECORATIVE

Return ONLY the alt text string or the word DECORATIVE.\
"""


# ── Claude client (cached per session) ───────────────────────────────────────
@st.cache_resource(ttl=3600)
def _get_claude_client() -> object:
    import anthropic

    return anthropic.Anthropic(api_key=st.secrets["anthropic"]["api_key"])


# ── Helpers ───────────────────────────────────────────────────────────────────
def _classify(img_url: str, page_path: str) -> str:
    folder = detect_folder(img_url)
    if folder == "unknown":
        return "unknown"
    if folder in CAPTION_MAP.get(page_path, {}):
        return "manual"
    return "folder_fallback"


def _collect(cache: dict[str, Any], mode: str) -> list[dict[str, str]]:
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
            cls = _classify(src, page_path)
            if mode == "unknown-only" and cls != "unknown":
                continue
            if mode == "fallback" and cls == "manual":
                continue
            candidates.append({
                "page_url":        page_url,
                "page_path":       page_path,
                "image_url":       src,
                "folder":          detect_folder(src),
                "caption_type":    cls,
                "current_caption": generate_caption(src, page_path),
            })
    return candidates


def _analyze_image(client: object, img_url: str, page_path: str, folder: str) -> str:
    import requests

    # Skip tracking pixels and non-image URLs
    skip_patterns = ("facebook.com/tr", "google-analytics", "googletagmanager")
    if any(p in img_url for p in skip_patterns):
        return "SKIP_NOT_IMAGE"

    try:
        resp = requests.get(
            img_url, timeout=12,
            headers={"User-Agent": "SalasarAltTextAudit/1.0"},
        )
        if resp.status_code != 200:
            return "DOWNLOAD_FAILED"
        content_type = resp.headers.get("Content-Type", "")
        if "text" in content_type or "javascript" in content_type or len(resp.content) < 100:
            return "SKIP_NOT_IMAGE"
        mime = content_type.split(";")[0].strip() or "image/jpeg"
        import base64
        img_b64 = base64.standard_b64encode(resp.content).decode("utf-8")
    except Exception:
        return "DOWNLOAD_FAILED"

    prompt = _PROMPT.format(
        page_url=f"https://www.salasarservices.com{page_path}",
        folder=folder,
    )
    try:
        response = client.messages.create(  # type: ignore[union-attr]
            model=_CLAUDE_MODEL,
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type":       "base64",
                            "media_type": mime,
                            "data":       img_b64,
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        text = response.content[0].text.strip()
        if text != "DECORATIVE" and len(text) > 120:
            text = text[:117] + "…"
        return text
    except Exception as exc:
        return f"API_ERROR: {str(exc)[:80]}"


def _caption_type_badge(t: str) -> str:
    colours = {
        "manual":          ("#16a34a", "#dcfce7"),
        "folder_fallback": ("#d97706", "#fef3c7"),
        "unknown":         ("#dc2626", "#fee2e2"),
    }
    fg, bg = colours.get(t, ("#64748b", "#f1f5f9"))
    return (
        f"<span style='background:{bg};color:{fg};padding:2px 8px;"
        f"border-radius:10px;font-size:.75em;font-weight:700'>{t}</span>"
    )


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown("## 🤖 Alt Text Audit")
st.caption(
    "Analyse website images with Gemini Vision · compare AI suggestions against "
    "current captions · approve in-browser · download CSV."
)

# ── Cache status ──────────────────────────────────────────────────────────────
cache = load_cache(_CACHE_PATH)

if not cache:
    st.warning(
        "⚠️ No crawl cache found. "
        "Run the **Sitemap Generator** page first, then come back here."
    )
    st.stop()

total_pages  = sum(1 for r in cache.values() if not r.get("excluded"))
total_images = sum(len(r.get("images", [])) for r in cache.values() if not r.get("excluded"))

st.success(
    f"📦 Cache loaded — **{total_pages}** pages · **{total_images:,}** images"
)
st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
with c1:
    mode = st.selectbox(
        "Image filter",
        ["fallback", "unknown-only", "all"],
        format_func=lambda x: {
            "fallback":     "Fallback only (folder_fallback + unknown)",
            "unknown-only": "Unknown folder only (strictest)",
            "all":          "All images (including manual)",
        }[x],
    )
with c2:
    limit = st.number_input("Max images", min_value=5, max_value=500, value=50, step=10)
with c3:
    all_images = st.checkbox("No limit", value=False)
with c4:
    run_btn = st.button("🚀 Run Audit", type="primary", use_container_width=True)

# ── Candidate summary ─────────────────────────────────────────────────────────
all_candidates = _collect(cache, mode)
to_audit = all_candidates if all_images else all_candidates[:limit]

cost_usd = len(to_audit) * 0.0001
m1, m2, m3, m4 = st.columns(4)
m1.metric("Total candidates", len(all_candidates))
m2.metric("Will analyse",     len(to_audit))
m3.metric("Est. cost",        f"${cost_usd:.4f}")
m4.metric("Est. cost (₹)",    f"₹{cost_usd * 84:.2f}")

st.divider()

# ── Run audit ─────────────────────────────────────────────────────────────────
if run_btn:
    if not to_audit:
        st.info("No images match this filter. Try changing the mode.")
        st.stop()

    model = _get_claude_client()
    progress_bar = st.progress(0)
    status_ph    = st.empty()
    results: list[dict[str, Any]] = []
    errors = 0

    for i, c in enumerate(to_audit, 1):
        pct = int(i / len(to_audit) * 100)
        progress_bar.progress(pct)
        status_ph.markdown(
            f"🤖 **Analysing…** &nbsp;"
            f"<code>{i} / {len(to_audit)}</code> &nbsp;·&nbsp; "
            f"`{c['image_url'].split('/')[-1][:50]}`",
            unsafe_allow_html=True,
        )

        ai = _analyze_image(model, c["image_url"], c["page_path"], c["folder"])
        is_err = ai.startswith(("DOWNLOAD_FAILED", "API_ERROR"))
        if is_err:
            errors += 1

        results.append({
            "page_url":        c["page_url"],
            "image_url":       c["image_url"],
            "folder":          c["folder"],
            "caption_type":    c["caption_type"],
            "current_caption": c["current_caption"],
            "ai_caption":      ai,
            "char_count":      len(ai) if not is_err else 0,
            "approved":        False,
            "promote_to_map":  False,
        })
        time.sleep(_RATE_SLEEP)

    progress_bar.progress(100)
    status_ph.success(
        f"✅ Done — **{len(results)}** analysed · **{errors}** errors"
    )
    st.session_state["audit_results"] = results
    st.session_state["audit_errors"]  = errors

# ── Results table ─────────────────────────────────────────────────────────────
if "audit_results" in st.session_state:
    results = st.session_state["audit_results"]
    errors  = st.session_state["audit_errors"]

    st.markdown("### Review Results")
    st.caption(
        "Tick **Approved** to accept an AI caption. "
        "Tick **Add to map** to permanently bake it into `captioner.py`. "
        "Edit any cell directly."
    )

    # Summary row
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Analysed",   len(results))
    r2.metric("Errors",     errors)
    r3.metric("Decorative", sum(1 for r in results if r["ai_caption"] == "DECORATIVE"))
    r4.metric("Over 120 chars",
              sum(1 for r in results if r["char_count"] > 120 and r["char_count"] > 0))

    df = pd.DataFrame(results)

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        height=500,
        column_config={
            "page_url": st.column_config.LinkColumn(
                "Page", display_text=r"https://www\.salasarservices\.com(.*)"
            ),
            "image_url": st.column_config.TextColumn("Image URL", width="medium"),
            "folder":          st.column_config.TextColumn("Folder",   width="small"),
            "caption_type":    st.column_config.TextColumn("Type",     width="small"),
            "current_caption": st.column_config.TextColumn("Current caption", width="large"),
            "ai_caption":      st.column_config.TextColumn("AI caption",      width="large"),
            "char_count":      st.column_config.NumberColumn("Chars", width="small"),
            "approved":        st.column_config.CheckboxColumn("✅ Approved",    width="small"),
            "promote_to_map":  st.column_config.CheckboxColumn("📌 Add to map",  width="small"),
        },
        disabled=["page_url", "image_url", "folder", "caption_type",
                  "current_caption", "char_count"],
        hide_index=True,
        key="audit_editor",
    )

    # Save edits back to session state
    st.session_state["audit_results"] = edited_df.to_dict(orient="records")

    st.divider()

    # ── Download ──────────────────────────────────────────────────────────────
    approved_count = int(edited_df["approved"].sum())
    promote_count  = int(edited_df["promote_to_map"].sum())

    dc1, dc2, dc3 = st.columns(3)
    dc1.metric("Approved",     approved_count)
    dc2.metric("Add to map",   promote_count)
    dc3.metric("Remaining",    len(results) - approved_count)

    csv_bytes = edited_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️  Download full audit CSV",
        data=csv_bytes,
        file_name="alt_text_audit.csv",
        mime="text/csv",
        use_container_width=True,
    )

    if promote_count > 0:
        promoted = edited_df[edited_df["promote_to_map"] == True][  # noqa: E712
            ["page_url", "image_url", "folder", "ai_caption"]
        ]
        with st.expander(f"📌 {promote_count} captions marked for CAPTION_MAP"):
            st.dataframe(promoted, use_container_width=True)
            st.info(
                "Share this list and I'll update `sitemap/captioner.py` "
                "automatically to make these permanent."
            )
