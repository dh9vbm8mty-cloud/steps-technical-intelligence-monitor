from __future__ import annotations

from typing import Any, Dict, List, Optional

from fetchers.base import FetchResult, maybe_sleep, request_with_retry
from models import RawItem


def fetch_openalex(source: Dict[str, Any], queries: List[str], limit: int) -> FetchResult:
    items: List[RawItem] = []
    last_error = None
    last_http_code = None
    for query in queries:
        params = {"search": query, "per-page": limit}
        response, error, http_code = request_with_retry(source, params=params)
        last_http_code = http_code
        if error or response is None:
            last_error = error
            continue
        payload = response.json()
        for entry in payload.get("results", []):
            title = entry.get("title")
            if not title:
                continue
            items.append(
                RawItem(
                    source_name=source["name"],
                    source_url=response.url,
                    item_type=detect_item_type(entry),
                    title=title,
                    canonical_url=entry.get("doi") or entry.get("id") or entry.get("primary_location", {}).get("landing_page_url"),
                    doi=entry.get("doi"),
                    authors=extract_authors(entry),
                    year=entry.get("publication_year"),
                    publication=extract_publication(entry),
                    abstract_or_summary=inverted_index_to_text(entry.get("abstract_inverted_index")),
                    raw_source_reference=entry,
                )
            )
        maybe_sleep(source)
    return FetchResult(items, last_error if not items else last_error, last_http_code)


def extract_authors(entry: Dict[str, Any]) -> List[str]:
    authors = []
    for authorship in entry.get("authorships", []):
        author = authorship.get("author", {}) if isinstance(authorship, dict) else {}
        name = author.get("display_name")
        if name:
            authors.append(name)
    return authors


def extract_publication(entry: Dict[str, Any]) -> Optional[str]:
    location = entry.get("primary_location") or {}
    source = location.get("source") or {}
    return source.get("display_name")


def inverted_index_to_text(index: Any) -> Optional[str]:
    if not isinstance(index, dict):
        return None
    words = []
    for word, positions in index.items():
        if isinstance(positions, list):
            for position in positions:
                words.append((position, word))
    return " ".join(word for _, word in sorted(words)) or None


def detect_item_type(entry: Dict[str, Any]) -> str:
    title = str(entry.get("title") or "").lower()
    work_type = str(entry.get("type") or "").lower()
    if "review" in title or work_type == "review":
        return "Review Paper"
    return "Research Paper"
