from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from sitemap.cache import is_fresh, upsert_record

BASE_URL = "https://www.salasarservices.com"

EXCLUSION_PATTERNS: list[str] = [
    r'/assets/',
    r'/uploads/',
    r'\.(jpg|jpeg|png|gif|svg|ico|webp|pdf|zip|doc|docx)$',
    r'\?',
    r'/#',
    r'/index\.html$',
    r'/linkedin\.com/',
    r'/assets/Frontend/images/upload-notes\.png',
    r'/assets/upload/client-image/-',
]

_COMPILED_EXCLUSIONS = [re.compile(p) for p in EXCLUSION_PATTERNS]

_HEADERS = {
    "User-Agent": "SalasarSitemapBot/1.0 (+https://www.salasarservices.com)",
    "Accept": "text/html,application/xhtml+xml",
}
_BATCH_SLEEP = 0.3
_MAX_WORKERS = 2
_MAX_RETRIES = 3


def should_exclude(url: str) -> bool:
    for pattern in _COMPILED_EXCLUSIONS:
        if pattern.search(url):
            return True
    return False


def _same_origin(url: str) -> bool:
    parsed = urlparse(url)
    base = urlparse(BASE_URL)
    return parsed.netloc in ("", base.netloc)


def _canonical_path(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path.rstrip('/') or '/'


def _fetch_with_retry(url: str) -> requests.Response | None:
    delay = 1.0
    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15, allow_redirects=True)
            if resp.status_code == 429:
                time.sleep(delay)
                delay *= 2
                continue
            return resp
        except requests.RequestException:
            if attempt < _MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
    return None


def _extract_images(soup: BeautifulSoup, page_url: str) -> list[dict[str, str]]:
    images = []
    for img in soup.find_all("img", src=True):
        src = img["src"].strip()
        if not src or src.startswith("data:"):
            continue
        abs_src = urljoin(page_url, src)
        images.append({"src": abs_src, "alt": img.get("alt", "").strip()})
    return images


def _crawl_url(url: str) -> dict[str, Any] | None:
    resp = _fetch_with_retry(url)
    if resp is None:
        return {"url": url, "http_status": 0, "excluded": True, "exclusion_reason": "fetch_failed", "images": []}

    final_url = resp.url
    if should_exclude(final_url):
        return None

    content_type = resp.headers.get("Content-Type", "")
    if "text/html" not in content_type:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    noindex = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
    if noindex:
        content = noindex.get("content", "")
        if "noindex" in content.lower():
            return {
                "url": final_url,
                "http_status": resp.status_code,
                "excluded": True,
                "exclusion_reason": "noindex",
                "images": [],
            }

    canonical_tag = soup.find("link", rel="canonical")
    canonical = canonical_tag["href"].strip() if canonical_tag and canonical_tag.get("href") else final_url

    last_modified = resp.headers.get("Last-Modified", "")
    images = _extract_images(soup, final_url)

    internal_links: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(final_url, a["href"].strip())
        if _same_origin(href) and not should_exclude(href):
            parsed = urlparse(href)
            clean = parsed._replace(fragment="", query="").geturl()
            internal_links.add(clean)

    return {
        "url": canonical,
        "http_status": resp.status_code,
        "last_modified": last_modified,
        "images": images,
        "internal_links": list(internal_links),
        "excluded": False,
        "exclusion_reason": "",
    }


def _seed_from_sitemap(base_url: str) -> set[str]:
    urls: set[str] = set()
    try:
        resp = _fetch_with_retry(f"{base_url}/sitemap.xml")
        if resp is None or resp.status_code != 200:
            return urls
        soup = BeautifulSoup(resp.text, "xml")
        for loc in soup.find_all("loc"):
            url = loc.get_text(strip=True)
            if _same_origin(url) and not should_exclude(url):
                urls.add(url)
    except Exception:
        pass
    return urls


def crawl(
    base_url: str = BASE_URL,
    cache: dict[str, Any] | None = None,
    force: bool = False,
    verbose: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if cache is None:
        cache = {}

    queue: set[str] = _seed_from_sitemap(base_url)
    queue.add(base_url + "/")
    visited: set[str] = set()
    results: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    def _process(url: str) -> dict[str, Any] | None:
        if not force and url in cache and is_fresh(cache[url]):
            if verbose:
                print(f"  [cache] {url}")
            return cache[url]
        if verbose:
            print(f"  [fetch] {url}")
        return _crawl_url(url)

    while queue:
        batch = list(queue - visited)[:_MAX_WORKERS * 4]
        visited.update(batch)
        queue -= set(batch)

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = {executor.submit(_process, url): url for url in batch}
            for future in as_completed(futures):
                record = future.result()
                if record is None:
                    continue
                upsert_record(cache, record["url"], record)
                if record.get("excluded"):
                    excluded.append(record)
                else:
                    results.append(record)
                    for link in record.get("internal_links", []):
                        if link not in visited and not should_exclude(link):
                            queue.add(link)

        if queue:
            time.sleep(_BATCH_SLEEP)

    seen_urls: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for r in results:
        if r["url"] not in seen_urls:
            seen_urls.add(r["url"])
            deduped.append(r)

    return deduped, excluded
