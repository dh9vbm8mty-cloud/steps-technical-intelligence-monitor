from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fetchers.base import FetchResult, request_with_retry
from models import RawItem


def fetch_generic_html(source: Dict[str, Any], queries: List[str], limit: int) -> FetchResult:
    response, error, http_code = request_with_retry(source)
    if error or response is None:
        return FetchResult([], error, http_code)
    soup = BeautifulSoup(response.text, "html.parser")
    items: List[RawItem] = []
    for anchor in soup.find_all("a", href=True):
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not title or len(title) < 12:
            continue
        href = urljoin(response.url, anchor["href"])
        items.append(
            RawItem(
                source_name=source["name"],
                source_url=response.url,
                item_type=source.get("item_type", "Other Relevant Evidence"),
                title=title,
                canonical_url=href,
                raw_source_reference={"href": anchor["href"]},
            )
        )
        if len(items) >= limit:
            break
    return FetchResult(items, None, http_code)
