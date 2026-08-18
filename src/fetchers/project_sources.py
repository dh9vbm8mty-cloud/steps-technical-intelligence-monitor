from __future__ import annotations

from typing import Any, Dict, List

from fetchers.base import FetchResult
from fetchers.generic_feed import fetch_generic_feed
from fetchers.generic_html import fetch_generic_html


def fetch_project_source(source: Dict[str, Any], queries: List[str], limit: int) -> FetchResult:
    source_type = source.get("type")
    if source_type == "generic_feed":
        result = fetch_generic_feed(source, queries, limit)
    else:
        result = fetch_generic_html(source, queries, limit)
    for item in result.items:
        item.item_type = infer_project_item_type(item.title)
    return result


def infer_project_item_type(title: str) -> str:
    text = title.lower()
    if any(term in text for term in ["pilot", "demonstration", "demo"]):
        return "Demonstration Project"
    if any(term in text for term in ["deployment", "commercial", "product"]):
        return "Commercial Deployment"
    if any(term in text for term in ["program", "funding", "project"]):
        return "Government / Public R&D Program"
    return "Other Relevant Evidence"
