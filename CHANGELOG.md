# Changelog — Digital Marketing Dashboard

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
