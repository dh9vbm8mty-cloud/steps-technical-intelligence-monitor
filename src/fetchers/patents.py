from __future__ import annotations

import re
from typing import Any, Dict, List
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from fetchers.base import FetchResult, request_with_retry
from models import RawItem


def fetch_patents_fallback(source: Dict[str, Any], queries: List[str], limit: int) -> FetchResult:
    response, error, http_code = request_with_retry(source)
    if error or response is None:
        return FetchResult([], error, http_code)
    soup = BeautifulSoup(response.text, "html.parser")
    items: List[RawItem] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if "/patent/" not in href:
            continue
        title = " ".join(anchor.get_text(" ", strip=True).split())
        patent_number = extract_patent_number(href)
        if not title or not patent_number:
            continue
        items.append(
            RawItem(
                source_name=source["name"],
                source_url=response.url,
                item_type="Patent",
                title=title,
                canonical_url=urljoin(response.url, href),
                patent_publication_number=patent_number,
                raw_source_reference={
                    "href": href,
                    "phase_1_limitation": "Google Patents fallback HTML result; human patent review required.",
                },
            )
        )
        if len(items) >= limit:
            break
    return FetchResult(items, None, http_code)


def extract_patent_number(href: str) -> str | None:
    match = re.search(r"/patent/([^/?#]+)", href)
    if not match:
        return None
    return match.group(1)
