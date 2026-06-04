from __future__ import annotations

import os
from typing import Any
from urllib.parse import urlparse
from xml.dom import minidom
from xml.etree import ElementTree as ET

from sitemap.captioner import generate_caption

_NS_SITEMAP = "http://www.sitemaps.org/schemas/sitemap/0.9"
_NS_IMAGE   = "http://www.google.com/schemas/sitemap-image/1.1"

ET.register_namespace("",      _NS_SITEMAP)
ET.register_namespace("image", _NS_IMAGE)


def _tag(ns: str, local: str) -> str:
    return f"{{{ns}}}{local}"


def _pretty(element: ET.Element) -> str:
    raw = ET.tostring(element, encoding="unicode", xml_declaration=False)
    dom = minidom.parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}')
    return dom.toprettyxml(indent="  ", encoding=None)


def _sort_key(page: dict[str, Any]) -> tuple[int, float, str]:
    url = page["url"]
    path = urlparse(url).path.rstrip("/") or "/"
    is_home = 1 if path == "/" else 0
    priority = page.get("priority", 0.5)
    return (-is_home, -priority, url)


def _parse_lastmod(raw: str) -> str | None:
    if not raw:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            from datetime import datetime
            dt = datetime.strptime(raw.strip(), fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def build(pages: list[dict[str, Any]], output_dir: str = "output") -> tuple[str, str]:
    os.makedirs(output_dir, exist_ok=True)

    eligible = [
        p for p in pages
        if not p.get("excluded") and p.get("http_status", 0) < 400
    ]
    eligible.sort(key=_sort_key)

    # ET.register_namespace() at module level handles xmlns declarations
    # automatically — do NOT also pass them in attrib or minidom will see
    # duplicate attributes and raise "duplicate attribute" on parse-back.
    urlset = ET.Element(_tag(_NS_SITEMAP, "urlset"))

    for page in eligible:
        url_el = ET.SubElement(urlset, _tag(_NS_SITEMAP, "url"))

        ET.SubElement(url_el, _tag(_NS_SITEMAP, "loc")).text = page["url"]

        lastmod = _parse_lastmod(page.get("last_modified", ""))
        if lastmod:
            ET.SubElement(url_el, _tag(_NS_SITEMAP, "lastmod")).text = lastmod

        ET.SubElement(url_el, _tag(_NS_SITEMAP, "changefreq")).text = page.get("changefreq", "monthly")
        ET.SubElement(url_el, _tag(_NS_SITEMAP, "priority")).text = str(page.get("priority", 0.5))

        page_path = urlparse(page["url"]).path.rstrip("/") or "/"
        for img in page.get("images", []):
            src = img.get("src", "").strip()
            if not src:
                continue
            img_el = ET.SubElement(url_el, _tag(_NS_IMAGE, "image"))
            ET.SubElement(img_el, _tag(_NS_IMAGE, "loc")).text = src
            caption = generate_caption(src, page_path)
            ET.SubElement(img_el, _tag(_NS_IMAGE, "caption")).text = caption

    sitemap_path = os.path.join(output_dir, "sitemap.xml")
    xml_str = _pretty(urlset)
    with open(sitemap_path, "w", encoding="utf-8") as fh:
        fh.write(xml_str)

    parsed_back = ET.parse(sitemap_path)
    actual_count = len(parsed_back.getroot().findall(_tag(_NS_SITEMAP, "url")))
    assert actual_count == len(eligible), (
        f"Post-write assertion failed: wrote {len(eligible)} URLs but parsed back {actual_count}"
    )

    index = ET.Element(_tag(_NS_SITEMAP, "sitemapindex"))
    sm_el = ET.SubElement(index, _tag(_NS_SITEMAP, "sitemap"))
    ET.SubElement(sm_el, _tag(_NS_SITEMAP, "loc")).text = "https://www.salasarservices.com/sitemap.xml"

    index_path = os.path.join(output_dir, "sitemap-index.xml")
    with open(index_path, "w", encoding="utf-8") as fh:
        fh.write(_pretty(index))

    return sitemap_path, index_path
