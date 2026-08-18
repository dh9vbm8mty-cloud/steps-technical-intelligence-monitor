from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import yaml

from classify import classify_items
from dedup import append_items_jsonl, apply_dedup, load_seen, save_seen
from fetchers import fetch_crossref, fetch_openalex, fetch_patents_fallback, fetch_project_source, fetch_semantic_scholar
from models import IntelligenceItem, RawItem, SourceHealthRecord
from normalize import normalize_raw_item, utc_now, utc_now_iso
from report_daily import generate_daily_reports
from report_weekly import generate_weekly_reports
from source_health import degraded_sources, load_source_health, record_failure, record_partial_success, record_success, save_source_health


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def query_families(taxonomy: Dict[str, Any]) -> List[str]:
    queries: List[str] = []
    for values in taxonomy.get("search_families", {}).values():
        queries.extend(values)
    return queries


def run_monitor(project_root: Path, mode: str) -> Dict[str, Any]:
    settings = load_yaml(project_root / "config" / "settings.yaml")
    sources_config = load_yaml(project_root / "config" / "sources.yaml")
    taxonomy = load_yaml(project_root / "config" / "taxonomy.yaml")
    registry = settings["registry"]
    source_health_path = project_root / registry["source_health_path"]
    seen_path = project_root / registry["seen_items_path"]
    items_path = project_root / registry["items_path"]
    runs_dir = project_root / registry["runs_dir"]
    runs_dir.mkdir(parents=True, exist_ok=True)

    source_health = load_source_health(source_health_path)
    raw_items, errors = fetch_all_sources(sources_config, taxonomy, settings, source_health, mode)
    normalized_items = [normalize_raw_item(raw) for raw in raw_items if raw.title.strip()]
    classified_items = classify_items(normalized_items, taxonomy)

    seen = load_seen(seen_path)
    deduped_items = apply_dedup(classified_items, seen)
    save_seen(seen_path, seen)
    append_items_jsonl(items_path, [item for item in deduped_items if item.status in {"NEW", "UPDATED"}])
    save_source_health(source_health_path, source_health)

    run_summary = build_run_summary(raw_items, deduped_items, errors, source_health)
    run_payload = build_run_payload(run_summary, deduped_items, errors, source_health)
    run_path = runs_dir / f"{utc_now()}.json"
    run_path.write_text(json.dumps(run_payload, indent=2, sort_keys=True), encoding="utf-8")

    daily_paths = generate_daily_reports(deduped_items, run_summary, source_health, settings, project_root)
    weekly_paths = generate_weekly_reports(project_root)
    return {
        "run_path": str(run_path),
        "daily_reports": [str(path) for path in daily_paths],
        "weekly_reports": [str(path) for path in weekly_paths],
        "summary": run_summary,
        "source_health": {name: record.to_dict() for name, record in sorted(source_health.items())},
    }


def fetch_all_sources(
    sources_config: Dict[str, Any],
    taxonomy: Dict[str, Any],
    settings: Dict[str, Any],
    source_health: Dict[str, SourceHealthRecord],
    mode: str,
) -> tuple[List[RawItem], List[Dict[str, Any]]]:
    all_queries = query_families(taxonomy)
    max_queries = int(settings["run"]["backfill_max_queries"] if mode == "backfill" else settings["run"]["monitor_max_queries"])
    queries = all_queries[:max_queries]
    limit = int(settings["run"]["backfill_query_limit_per_source"] if mode == "backfill" else settings["run"]["monitor_query_limit_per_source"])
    raw_items: List[RawItem] = []
    errors: List[Dict[str, Any]] = []

    for source in sources_config.get("academic_sources", []):
        if not source.get("enabled", True):
            continue
        try:
            result = dispatch_academic_fetcher(source, queries, limit)
        except Exception as exc:
            record_failure(source_health, source["name"], f"parser or fetcher exception: {exc}")
            errors.append({"source_name": source["name"], "error": str(exc)})
            continue
        raw_items.extend(result.items)
        update_health(source_health, source["name"], result)
        if result.error:
            errors.append({"source_name": source["name"], "error": result.error})

    for source in sources_config.get("project_sources", []):
        if not source.get("enabled", True):
            continue
        try:
            result = fetch_project_source(source, queries, limit)
        except Exception as exc:
            record_failure(source_health, source["name"], f"parser or fetcher exception: {exc}")
            errors.append({"source_name": source["name"], "error": str(exc)})
            continue
        raw_items.extend(result.items)
        update_health(source_health, source["name"], result)
        if result.error:
            errors.append({"source_name": source["name"], "error": result.error})

    for source in sources_config.get("patent_sources", []):
        if not source.get("enabled", False):
            continue
        try:
            result = fetch_patents_fallback(source, queries, limit)
        except Exception as exc:
            record_failure(source_health, source["name"], f"parser or fetcher exception: {exc}")
            errors.append({"source_name": source["name"], "error": str(exc)})
            continue
        raw_items.extend(result.items)
        update_health(source_health, source["name"], result)
        if result.error:
            errors.append({"source_name": source["name"], "error": result.error})

    return raw_items, errors


def dispatch_academic_fetcher(source: Dict[str, Any], queries: List[str], limit: int):
    source_type = source.get("type")
    if source_type == "crossref":
        return fetch_crossref(source, queries, limit)
    if source_type == "openalex":
        return fetch_openalex(source, queries, limit)
    if source_type == "semantic_scholar":
        return fetch_semantic_scholar(source, queries, limit)
    raise ValueError(f"Unsupported academic source type: {source_type}")


def update_health(source_health: Dict[str, SourceHealthRecord], source_name: str, result: Any) -> None:
    if result.error and not result.items:
        record_failure(source_health, source_name, result.error, result.http_code, len(result.items))
    elif result.error and result.items:
        record_partial_success(source_health, source_name, result.error, len(result.items), result.http_code)
    else:
        record_success(source_health, source_name, len(result.items), result.http_code)


def build_run_summary(
    raw_items: List[RawItem],
    items: List[IntelligenceItem],
    errors: List[Dict[str, Any]],
    source_health: Dict[str, SourceHealthRecord],
) -> Dict[str, Any]:
    return {
        "raw_item_count": len(raw_items),
        "normalized_item_count": len(items),
        "new_item_count": count_status(items, "NEW"),
        "updated_item_count": count_status(items, "UPDATED"),
        "duplicate_item_count": count_status(items, "DUPLICATE") + count_status(items, "PREVIOUSLY_SEEN"),
        "rejected_item_count": count_status(items, "REJECTED"),
        "error_count": len(errors),
        "degraded_source_count": len(degraded_sources(source_health)),
    }


def build_run_payload(
    run_summary: Dict[str, Any],
    items: List[IntelligenceItem],
    errors: List[Dict[str, Any]],
    source_health: Dict[str, SourceHealthRecord],
) -> Dict[str, Any]:
    return {
        "run_timestamp": utc_now_iso(),
        "source_health": {name: record.to_dict() for name, record in sorted(source_health.items())},
        "degraded_sources": [record.to_dict() for record in degraded_sources(source_health).values()],
        "raw_item_count": run_summary["raw_item_count"],
        "normalized_item_count": run_summary["normalized_item_count"],
        "new_items": [item.to_dict() for item in items if item.status == "NEW"],
        "updated_items": [item.to_dict() for item in items if item.status == "UPDATED"],
        "duplicates": [item.to_dict() for item in items if item.status in {"DUPLICATE", "PREVIOUSLY_SEEN"}],
        "rejected_items": [item.to_dict() for item in items if item.status == "REJECTED"],
        "errors": errors,
    }


def count_status(items: List[IntelligenceItem], status: str) -> int:
    return sum(1 for item in items if item.status == status)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["monitor", "backfill"], default="monitor")
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    result = run_monitor(Path(args.root), args.mode)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
