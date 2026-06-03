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


def _query_gsc_page(sc_client: Any, site_url: str, page_url: str) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=90)
    try:
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["page"],
            "dimensionFilterGroups": [{
                "filters": [{
                    "dimension": "page",
                    "operator": "equals",
                    "expression": page_url,
                }]
            }],
            "rowLimit": 1,
        }
        rows = sc_client.searchanalytics().query(siteUrl=site_url, body=body).execute().get("rows", [])
        if not rows:
            return {}
        row = rows[0]
        return {
            "gsc_clicks":      row.get("clicks", 0),
            "gsc_impressions": row.get("impressions", 0),
            "gsc_ctr":         row.get("ctr", 0.0),
            "gsc_position":    row.get("position"),
        }
    except Exception:
        return {}


def enrich(
    pages: list[dict[str, Any]],
    sc_client: Any,
    site_url: str,
) -> list[dict[str, Any]]:
    for page in pages:
        url = page["url"]
        gsc = _query_gsc_page(sc_client, site_url, url)

        impressions = gsc.get("gsc_impressions", 0)
        position = gsc.get("gsc_position")
        is_hp = url.rstrip("/") == site_url.rstrip("/")

        page["gsc_clicks"] = gsc.get("gsc_clicks", 0)
        page["gsc_impressions"] = impressions
        page["gsc_ctr"] = gsc.get("gsc_ctr", 0.0)
        page["gsc_position"] = position
        page["priority"] = derive_priority(impressions, is_hp)
        page["changefreq"] = derive_changefreq(impressions, position)

    return pages
