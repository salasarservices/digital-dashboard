# Changelog — Digital Marketing Dashboard

---

## [3.1.0] — 2026-06-04

### Alt Text Audit — Gemini Vision

New Streamlit page and CLI script that analyses every website image using Google Gemini 1.5 Flash, compares AI-generated captions against current sitemap captions, and presents a side-by-side review table.

#### New files

| File | Description |
|---|---|
| `pages/alt_text_audit.py` | Streamlit page — run audit in-browser, review in `st.data_editor`, download CSV |
| `scripts/audit_alt_text.py` | CLI equivalent — `--limit`, `--all-images`, `--mode`, `--dry-run`, `--verbose` |

#### How it works

1. Reads `output/sitemap_cache.json` (populated by Sitemap Generator — no re-crawl needed)
2. Classifies every image as `manual` (in `CAPTION_MAP`), `folder_fallback`, or `unknown`
3. Sends non-manual images to `gemini-1.5-flash` with page context prompt
4. Authenticates via existing GCP service account (`gcp.service_account`) — no new API key required
5. Returns AI caption alongside current caption for side-by-side review

#### Gemini prompt design

Each image is sent with:
- Page URL for context
- Image folder category (`product-image`, `Leadership_image`, etc.)
- Rules: max 120 chars, end with `| Salasar Services`, no "Image of", DECORATIVE for non-informational images

#### Cost

~$0.0001 per image (~₹0.008). Full site audit of 5,000 images ≈ $0.50.

#### Review workflow (Streamlit page)

- Live progress bar shows filename + counter during analysis
- `st.data_editor` table — editable `approved` and `promote_to_map` checkboxes per row
- Download button exports approved captions as CSV
- Captions marked `promote_to_map` are listed for permanent addition to `CAPTION_MAP`

#### Dependencies added

| Package | Purpose |
|---|---|
| `google-generativeai` | Gemini Vision API client |

---

## [3.0.0] — 2026-06-04

### Sitemap Generator

Production-grade sitemap generation module added as a multi-page Streamlit app extension and standalone CLI script.

#### New files

| File | Description |
|---|---|
| `sitemap/__init__.py` | Package root |
| `sitemap/captioner.py` | `CAPTION_MAP` (40+ manually-reviewed page+folder captions), `generate_caption()` |
| `sitemap/clients.py` | `build_gsc_client(sa_json)` — shared GSC client factory |
| `sitemap/cache.py` | JSON file cache — replaces MongoDB; `load_cache`, `save_cache`, `is_fresh`, `append_run_log`, `load_run_log` |
| `sitemap/crawler.py` | URL + image discovery; seeds from `/sitemap.xml`, follows internal links; `should_exclude()`, rate limiting, exponential backoff |
| `sitemap/gsc_enricher.py` | Single-call GSC batch query → `derive_priority()`, `derive_changefreq()`, `enrich()` |
| `sitemap/builder.py` | Standards-compliant XML assembly using stdlib only (`xml.etree.ElementTree` + `xml.dom.minidom`) |
| `pages/sitemap_generator.py` | Streamlit UI — last-run stats, live progress bar, force re-crawl, GSC toggle, download button, URL dataframe |
| `scripts/generate_sitemap.py` | CLI — `--force`, `--dry-run`, `--output`, `--no-gsc`, `--verbose`; exit codes 0/1/2 |
| `tests/test_captioner.py` | 6 pytest unit tests — all passing |
| `output/.gitkeep` | Ensures `output/` directory exists in repo; generated files are gitignored |
| `.gitignore` | Excludes `output/sitemap.xml`, `output/sitemap_cache.json`, `output/sitemap_runs.jsonl`, `__pycache__/`, `secrets.toml` |

#### Crawler

- Seeds from existing `/sitemap.xml`, then follows all internal links
- Per page: canonical URL, HTTP status, Last-Modified header, all `<img>` src + alt
- Skips `<meta name="robots" content="noindex">` pages
- Hard exclusion patterns: `/assets/`, `/uploads/`, image/doc extensions, query strings, LinkedIn, specific upload paths
- Rate limiting: `ThreadPoolExecutor(max_workers=2)`, 300ms sleep between batches
- Exponential backoff on HTTP 429, up to 3 retries
- `on_progress(done, in_queue, excluded)` callback for live UI updates

#### GSC enrichment

- Single paginated API call fetches all pages in one request (replaces per-URL queries — ~196× faster)
- Priority thresholds: homepage=1.0, >5000 impr=0.9, >1000=0.8, >200=0.7, >50=0.6, else=0.5
- `changefreq`: `"weekly"` only if impressions >200 AND position <10; otherwise `"monthly"`; never `"daily"`
- `on_progress(done, total)` callback

#### Image captions

- 40+ manually-reviewed captions in `CAPTION_MAP` keyed by `(page_path, folder)`
- Folder detection: Banner-Image, product-image, client-image, Certificate-Image, Leadership_image, Testimony_image, Claim-process, blog, career-image
- Blog images: caption derived from filename slug
- Fallbacks per folder type: consistent brand wording with page slug interpolation

#### XML output

- `sitemap.xml` — `<urlset>` with `xmlns:image` namespace; per URL: `<loc>`, `<lastmod>` (date only, omitted if unknown), `<changefreq>`, `<priority>`, `<image:image>` blocks with `<image:loc>` and `<image:caption>`
- `sitemap-index.xml` — points to `sitemap.xml`
- Sort order: homepage first → descending priority → alphabetical
- Post-write assertion: parses file back and verifies URL count matches
- Identical inputs produce byte-identical output (idempotent)

#### Cache

- `output/sitemap_cache.json` — URL-keyed, upserted on each run; 7-day freshness check
- `output/sitemap_runs.jsonl` — one JSON line per run (url_count, image_count, duration_seconds, status, triggered_by)
- `force=True` bypasses freshness check and re-crawls everything

#### Security

- Login gate (`st.session_state["logged_in"]`) at top of both new pages
- Sidebar nav hidden during login screen via CSS (`[data-testid="stSidebarNav"]`)
- No hardcoded credentials — all via `st.secrets["gcp"]["service_account"]`

#### Verified results

- Dry-run: 196 indexable URLs discovered, 45 excluded, exit code 0
- `pytest tests/test_captioner.py` — 6/6 passed

#### Dependencies added

| Package | Purpose |
|---|---|
| `beautifulsoup4` | HTML parsing in crawler |
| `tomli` | TOML parsing for CLI secrets fallback (Python < 3.11 backport) |
| `pytest` | Unit test runner |

---

## [2.0.0] — 2026-05-29

### Overview
Comprehensive SEO intelligence layer added to the Salasar Services Digital Marketing Dashboard. The update introduces deep-analysis sections for Google Search Console and Google Analytics 4, an automated insights engine, and a second parallel data-fetch pipeline — all without modifying any existing functionality.

---

## New Features

### 1. GA4 Deep Analysis Functions

#### `get_ga4_engagement(pid, sd, ed)`
Fetches site-wide engagement quality metrics from GA4.
- **Metrics returned:** `engagementRate`, `averageSessionDuration`, `screenPageViewsPerSession`, `bounceRate`
- **Use:** Powers the Engagement Quality KPI row in the Analytics Deep Dive section

#### `get_ga4_device_breakdown(pid, sd, ed)`
Breaks down sessions and engagement by device category.
- **Metrics returned:** `sessions`, `activeUsers`, `engagementRate`, `averageSessionDuration`
- **Dimensions:** `deviceCategory` (Mobile / Desktop / Tablet)
- **Use:** Device split table in Analytics Deep Dive

#### `get_ga4_landing_pages(pid, sd, ed, top_n=10)`
Top landing pages ranked by sessions with full engagement data.
- **Metrics returned:** `sessions`, `activeUsers`, `engagementRate`, `averageSessionDuration`, `bounceRate`
- **Dimension:** `landingPage`
- **Use:** Top 10 Landing Pages table in Analytics Deep Dive

#### `get_ga4_source_medium(pid, sd, ed, top_n=10)`
Traffic attribution broken down by source and medium.
- **Metrics returned:** `sessions`, `activeUsers`, `engagementRate`
- **Dimensions:** `sessionSource`, `sessionMedium`
- **Use:** Traffic by Source / Medium table in Analytics Deep Dive

#### `get_ga4_top_events(pid, sd, ed, top_n=10)`
Most-fired GA4 events ranked by count.
- **Metrics returned:** `eventCount`, `totalUsers`
- **Dimension:** `eventName`
- **Use:** Top Events table in Analytics Deep Dive

---

### 2. GSC Deep Analysis Functions

#### `get_gsc_query_report(site, sd, ed, limit=1000)`
Full keyword report — every query Google tracked for the site.
- **Fields returned:** `query`, `clicks`, `impressions`, `ctr`, `position`
- **Row limit:** 1,000 (up from 500 used in the original `get_search_console`)
- **Use:** Powers keyword table, position distribution KPIs, quick-win matrix, and insights engine

#### `get_gsc_page_full_report(site, sd, ed, limit=500)`
Page-level Search Console data with position and CTR per URL.
- **Fields returned:** `page`, `clicks`, `impressions`, `ctr`, `position`
- **Use:** Page-Level Search Performance table in GSC Deep Analysis

#### `get_gsc_device_report(site, sd, ed)`
Clicks, impressions, CTR and avg position split by device type.
- **Fields returned:** `device`, `clicks`, `impressions`, `ctr`, `position`
- **Devices:** Mobile, Desktop, Tablet
- **Use:** Performance by Device table in GSC Deep Analysis

---

### 3. SEO Insights Engine — `compute_seo_insights()`

A pure-Python analysis function that reads all GSC and GA4 data already in memory and generates four categorised output lists:

| Output key | Description |
|---|---|
| `improved` | Positive trend bullets shown in green — e.g. CTR up, new keywords in top 20, strong engagement rate |
| `attention` | Problem flags shown in amber — e.g. click drop, high bounce, zero-click high-impression keywords |
| `quick_wins` | Keyword-level opportunity rows (position, impressions, CTR, action) |
| `recommendations` | Strategic action items — topic clusters, featured snippets, Core Web Vitals, schema markup |

**Analysis logic covers:**
- Organic clicks delta vs previous period (>5% = improved, <-5% = attention)
- Impressions delta (>10% = improved, <-10% = attention)
- CTR quality — flags if average CTR < 2% with 500+ impressions
- Keyword position distribution change — top-3 count vs previous period
- Page-2 keywords (pos 11–20) with 50+ impressions → quick wins
- Below-average CTR on page-1 keywords → quick wins
- Zero-click keywords with 300+ impressions → featured snippet / PAA opportunity
- New keywords entering top 20 → confirms content momentum
- GA4 engagement rate benchmarking (>65% = good, <45% = attention)
- Average session duration (<45s = attention, >120s = improved)
- Bounce rate threshold (>65% triggers recommendation)
- User count delta vs previous period
- Pages-per-session depth check (<1.5 triggers internal linking recommendation)

---

### 4. Second Parallel Data Fetch Block

A second `ThreadPoolExecutor` (max 5 workers, 10 concurrent calls) runs immediately after the main data load. Covered calls:

```
get_ga4_engagement       × 2  (current + previous period)
get_ga4_device_breakdown × 1
get_ga4_landing_pages    × 1
get_ga4_source_medium    × 1
get_ga4_top_events       × 1
get_gsc_query_report     × 2  (current + previous period)
get_gsc_page_full_report × 1
get_gsc_device_report    × 1
```

All results are cached at 1 hour via `@st.cache_data(ttl=3600)`. A dedicated loading indicator (`show_loader`) is shown during this fetch and cleared on completion.

---

### 5. New Dashboard Sections

The dashboard now renders three additional sections, inserted between the existing Website Analytics section and the LinkedIn section.

#### Section A — Search Console Deep Analysis

| Component | Details |
|---|---|
| Position Distribution KPIs | Five cards: Top-3 keywords, Top-10 keywords, Page-2 keywords, Beyond position 20, Average position — all with prev-period deltas |
| Top 30 Keywords Table | Sorted by impressions; position badges colour-coded green (1-3) / blue (4-10) / amber (11-20) / red (21+); CTR badges green if above average, red if below |
| Performance by Device | GSC clicks, impressions, CTR and avg position per device |
| Quick Win Keywords | Keywords in positions 11–20 with 50+ impressions sorted by impressions |
| Page-Level Search Performance | Top 20 pages by clicks with CTR, impressions and colour-coded avg position |

#### Section B — Analytics Deep Dive

| Component | Details |
|---|---|
| Engagement Quality KPIs | Four cards: Engagement Rate, Avg Session Duration, Pages per Session, Bounce Rate — each with tooltip, formatted value and prev-period delta |
| Sessions by Device | Sessions, share %, engagement rate and avg duration per device |
| Traffic by Source / Medium | Sessions, users and engagement rate per source/medium pair |
| Top 10 Landing Pages | Sessions, engagement rate, avg duration and bounce rate per landing page |
| Top Events | Event name, total count and unique user reach |

#### Section C — SEO Insights & Action Plan

| Component | Details |
|---|---|
| What Improved (green card) | Live-computed positive trend bullets for the selected period |
| What Needs Attention (amber card) | Live-computed problem flags and issues |
| Strategic Recommendations (blue card) | Up to 5 prioritised action items |
| Keyword Quick Wins Table | Full table of quick-win keywords with position, impressions, CTR and specific action instructions |

---

## Dashboard Section Order (post-update)

1. Website Performance *(existing — GSC summary KPIs)*
2. Top Content *(existing — highest-clicked pages)*
3. **Search Console Deep Analysis** *(new)*
4. Website Analytics *(existing — GA4 summary KPIs)*
5. **Analytics Deep Dive** *(new)*
6. **SEO Insights & Action Plan** *(new)*
7. LinkedIn Analytics *(existing)*
8. Facebook Page Analytics *(existing)*
9. YouTube Channel Overview *(existing)*

---

## Files Changed

| File | Change |
|---|---|
| `dashboard.py` | +833 lines — 8 new data functions, 1 insights engine function, 1 parallel fetch block, 3 new rendering sections |

---

## No Breaking Changes

- All existing sections, functions, data variables and API clients are unchanged
- New data is fetched in a separate parallel block; the main data pipeline is unmodified
- No new dependencies — all APIs already imported
- Secrets schema unchanged
- PDF report generation unchanged
