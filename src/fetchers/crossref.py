from __future__ import annotations

from typing import Any, Dict, List, Optional

from fetchers.base import FetchResult, maybe_sleep, request_with_retry
from models import RawItem


def fetch_crossref(source: Dict[str, Any], queries: List[str], limit: int) -> FetchResult:
    items: List[RawItem] = []
    last_error = None
    last_http_code = None
    for query in queries:
        params = {"rows": limit, "query.title": query}
        response, error, http_code = request_with_retry(source, params=params)
        last_http_code = http_code
        if error or response is None:
            last_error = error
            continue
        payload = response.json()
        for entry in payload.get("message", {}).get("items", []):
            title = first_text(entry.get("title"))
            if not title:
                continue
            doi = entry.get("DOI")
            year = extract_year(entry)
            authors = [
                " ".join(part for part in [author.get("given"), author.get("family")] if part)
                for author in entry.get("author", [])
                if isinstance(author, dict)
            ]
            items.append(
                RawItem(
                    source_name=source["name"],
                    source_url=response.url,
                    item_type=detect_item_type(entry),
                    title=title,
                    canonical_url=entry.get("URL"),
                    doi=doi,
                    authors=authors,
                    year=year,
                    publication=first_text(entry.get("container-title")),
                    abstract_or_summary=entry.get("abstract"),
                    raw_source_reference=entry,
                )
            )
        maybe_sleep(source)
    return FetchResult(items, last_error if not items else last_error, last_http_code)


def first_text(value: Any) -> Optional[str]:
    if isinstance(value, list):
        for entry in value:
            if entry:
                return str(entry).strip()
    if isinstance(value, str):
        return value.strip()
    return None


def extract_year(entry: Dict[str, Any]) -> Optional[int]:
    for key in ("published-print", "published-online", "issued", "created"):
        parts = entry.get(key, {}).get("date-parts")
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                return None
    return None


def detect_item_type(entry: Dict[str, Any]) -> str:
    title = (first_text(entry.get("title")) or "").lower()
    crossref_type = str(entry.get("type", "")).lower()
    if "review" in title:
        return "Review Paper"
    if "standard" in crossref_type or "standard" in title or "test method" in title:
        return "Standard / Test Method"
    return "Research Paper"
