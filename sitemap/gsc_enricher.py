from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def derive_priority(impressions: int, is_homepage: bool) -> float:
    if is_homepage:
        return 1.0
    if impressions > 5000:
        return 0.9
    if impressions > 1000:
        return 0.8
    if impressions > 200:
        return 0.7
    if impressions > 50:
        return 0.6
    return 0.5


def derive_changefreq(impressions: int, position: float | None) -> str:
    if impressions > 200 and position is not None and position < 10:
        return "weekly"
    return "monthly"


def _fetch_all_gsc_pages(sc_client: Any, site_url: str) -> dict[str, dict[str, Any]]:
    """Single paginated API call — all pages for the last 90 days."""
    end = date.today()
    start = end - timedelta(days=90)
    result: dict[str, dict[str, Any]] = {}
    start_row = 0
    row_limit = 1000
    while True:
        try:
            body = {
                "startDate":  start.isoformat(),
                "endDate":    end.isoformat(),
                "dimensions": ["page"],
                "rowLimit":   row_limit,
                "startRow":   start_row,
            }
            rows = (
                sc_client.searchanalytics()
                .query(siteUrl=site_url, body=body)
                .execute()
                .get("rows", [])
            )
        except Exception:
            break
        for row in rows:
            url = row["keys"][0]
            result[url] = {
                "gsc_clicks":      row.get("clicks", 0),
                "gsc_impressions": row.get("impressions", 0),
                "gsc_ctr":         row.get("ctr", 0.0),
                "gsc_position":    row.get("position"),
            }
        if len(rows) < row_limit:
            break
        start_row += row_limit
    return result


def enrich(
    pages: list[dict[str, Any]],
    sc_client: Any,
    site_url: str,
    on_progress: object = None,
) -> list[dict[str, Any]]:
    """
    Enrich pages with GSC data using a single paginated API call.

    on_progress(done: int, total: int) is called after each page is enriched.
    """
    gsc_data = _fetch_all_gsc_pages(sc_client, site_url)
    total = len(pages)

    for i, page in enumerate(pages):
        url = page["url"]
        gsc = gsc_data.get(url, {})

        impressions = gsc.get("gsc_impressions", 0)
        position = gsc.get("gsc_position")
        is_hp = url.rstrip("/") == site_url.rstrip("/")

        page["gsc_clicks"] = gsc.get("gsc_clicks", 0)
        page["gsc_impressions"] = impressions
        page["gsc_ctr"] = gsc.get("gsc_ctr", 0.0)
        page["gsc_position"] = position
        page["priority"] = derive_priority(impressions, is_hp)
        page["changefreq"] = derive_changefreq(impressions, position)

        if on_progress is not None:
            on_progress(i + 1, total)

    return pages
