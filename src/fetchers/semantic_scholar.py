from __future__ import annotations

from typing import Any, Dict, List, Optional

from fetchers.base import FetchResult, maybe_sleep, request_with_retry
from models import RawItem


def fetch_semantic_scholar(source: Dict[str, Any], queries: List[str], limit: int) -> FetchResult:
    items: List[RawItem] = []
    last_error = None
    last_http_code = None
    for query in queries:
        params = {
            "query": query,
            "limit": limit,
            "fields": "title,url,abstract,year,authors,venue,externalIds,publicationTypes",
        }
        response, error, http_code = request_with_retry(source, params=params)
        last_http_code = http_code
        if error or response is None:
            last_error = error
            continue
        payload = response.json()
        for entry in payload.get("data", []):
            title = entry.get("title")
            if not title:
                continue
            external_ids = entry.get("externalIds") or {}
            items.append(
                RawItem(
                    source_name=source["name"],
                    source_url=response.url,
                    item_type=detect_item_type(entry),
                    title=title,
                    canonical_url=entry.get("url"),
                    doi=external_ids.get("DOI"),
                    authors=extract_authors(entry),
                    year=entry.get("year"),
                    publication=entry.get("venue"),
                    abstract_or_summary=entry.get("abstract"),
                    raw_source_reference=entry,
                )
            )
        maybe_sleep(source)
    return FetchResult(items, last_error if not items else last_error, last_http_code)


def extract_authors(entry: Dict[str, Any]) -> List[str]:
    authors = []
    for author in entry.get("authors", []):
        if isinstance(author, dict) and author.get("name"):
            authors.append(author["name"])
    return authors


def detect_item_type(entry: Dict[str, Any]) -> str:
    title = str(entry.get("title") or "").lower()
    publication_types = [str(value).lower() for value in (entry.get("publicationTypes") or [])]
    if "review" in title or "review" in publication_types:
        return "Review Paper"
    return "Research Paper"
