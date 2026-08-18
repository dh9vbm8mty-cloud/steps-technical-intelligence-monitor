from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from models import IntelligenceItem


def load_seen(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"items": {}, "index": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"items": {}, "index": {}}
    payload.setdefault("items", {})
    payload.setdefault("index", {})
    return payload


def save_seen(path: Path, seen: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(seen, indent=2, sort_keys=True), encoding="utf-8")


def load_items_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def append_items_jsonl(path: Path, items: Iterable[IntelligenceItem]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for item in items:
            handle.write(json.dumps(item.to_dict(), sort_keys=True) + "\n")


def item_keys(item: IntelligenceItem) -> List[str]:
    keys = []
    if item.DOI:
        keys.append(f"doi:{item.DOI}")
    if item.patent_publication_number:
        keys.append(f"patent:{item.patent_publication_number}")
    if item.canonical_url:
        keys.append(f"url:{item.canonical_url}")
    if item.normalized_title:
        keys.append(f"title:{item.normalized_title}")
    if item.normalized_title and item.organization and item.year:
        keys.append(f"title_org_year:{item.normalized_title}|{item.organization.lower()}|{item.year}")
    if item.normalized_title and item.organization and (item.location or item.country):
        location = (item.location or item.country or "").lower()
        keys.append(f"project_org_location:{item.normalized_title}|{item.organization.lower()}|{location}")
    return keys


def classify_against_seen(item: IntelligenceItem, seen: Dict[str, Any]) -> Tuple[str, Optional[str], List[str]]:
    index = seen.get("index", {})
    existing_id = None
    for key in item_keys(item):
        if key in index:
            existing_id = index[key]
            break
    if not existing_id:
        return "NEW", None, []
    existing = seen.get("items", {}).get(existing_id, {})
    update_reasons = detect_updates(existing, item)
    if update_reasons:
        return "UPDATED", existing_id, update_reasons
    return "PREVIOUSLY_SEEN", existing_id, []


def detect_updates(existing: Dict[str, Any], item: IntelligenceItem) -> List[str]:
    reasons = []
    candidate = item.to_dict()
    fields = (
        "abstract_or_summary",
        "canonical_url",
        "DOI",
        "patent_publication_number",
        "publication",
        "year",
        "organization",
        "country",
        "location",
        "project_maturity",
        "validation_quality",
    )
    for field in fields:
        old = existing.get(field)
        new = candidate.get(field)
        if (old in (None, "", [], "Unknown", "Not Reported")) and new not in (None, "", [], "Unknown", "Not Reported"):
            reasons.append(f"new_{field}")
    return reasons


def register_item(item: IntelligenceItem, seen: Dict[str, Any]) -> None:
    items = seen.setdefault("items", {})
    index = seen.setdefault("index", {})
    existing_id = item.duplicate_of or item.internal_id
    stored = item.to_dict()
    if existing_id in items:
        previous = items[existing_id]
        previous.update({key: value for key, value in stored.items() if value not in (None, "", [], "Unknown", "Not Reported")})
        previous["last_seen_at"] = item.last_seen_at
        previous["status"] = item.status
        previous["update_reasons"] = item.update_reasons
        items[existing_id] = previous
    else:
        items[existing_id] = stored
    for key in item_keys(item):
        index[key] = existing_id


def apply_dedup(items: List[IntelligenceItem], seen: Dict[str, Any]) -> List[IntelligenceItem]:
    run_index: Dict[str, str] = {}
    for item in items:
        if item.status == "REJECTED" or item.relevance == "Reject":
            item.status = "REJECTED"
            continue
        duplicate_id = None
        for key in item_keys(item):
            if key in run_index:
                duplicate_id = run_index[key]
                break
        if duplicate_id:
            item.status = "DUPLICATE"
            item.duplicate_of = duplicate_id
            continue
        status, existing_id, update_reasons = classify_against_seen(item, seen)
        item.status = status
        item.duplicate_of = existing_id
        item.update_reasons = update_reasons
        register_item(item, seen)
        for key in item_keys(item):
            run_index[key] = item.duplicate_of or item.internal_id
    return items
