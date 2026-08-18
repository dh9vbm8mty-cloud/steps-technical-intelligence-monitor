from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fetchers.base import FetchResult, request_with_retry
from models import RawItem


def fetch_generic_feed(source: Dict[str, Any], queries: List[str], limit: int) -> FetchResult:
    response, error, http_code = request_with_retry(source)
    if error or response is None:
        return FetchResult([], error, http_code)
    soup = BeautifulSoup(response.text, "xml")
    items: List[RawItem] = []
    for entry in soup.find_all(["item", "entry"]):
        title = get_text(entry, ["title", "name"])
        if not title:
            continue
        link = get_link(entry)
        items.append(
            RawItem(
                source_name=source["name"],
                source_url=response.url,
                item_type=source.get("item_type", "Other Relevant Evidence"),
                title=title,
                canonical_url=urljoin(response.url, link) if link else None,
                abstract_or_summary=get_text(entry, ["summary", "description"]),
                raw_source_reference={"link": link},
            )
        )
        if len(items) >= limit:
            break
    return FetchResult(items, None, http_code)


def get_text(tag: Any, names: List[str]) -> str:
    for name in names:
        element = tag.find(name)
        if element is not None and element.get_text(strip=True):
            return element.get_text(" ", strip=True)
    return ""


def get_link(tag: Any) -> str:
    link = tag.find("link")
    if link is None:
        return ""
    if link.get("href"):
        return link.get("href")
    return link.get_text(strip=True)
