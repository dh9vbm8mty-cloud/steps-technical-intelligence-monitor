from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

from models import SourceHealthRecord
from normalize import utc_now_iso


def load_source_health(path: Path) -> Dict[str, SourceHealthRecord]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    records = {}
    for name, data in payload.items():
        if isinstance(data, dict):
            records[name] = SourceHealthRecord(**data)
    return records


def save_source_health(path: Path, records: Dict[str, SourceHealthRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {name: record.to_dict() for name, record in sorted(records.items())}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def record_success(records: Dict[str, SourceHealthRecord], source_name: str, item_count: int, http_code: Optional[int] = None) -> None:
    now = utc_now_iso()
    record = records.get(source_name, SourceHealthRecord(source_name=source_name))
    record.last_attempt_at = now
    record.last_success_at = now
    record.last_status = "success"
    record.last_http_code = http_code
    record.consecutive_failures = 0
    record.item_count = item_count
    record.last_error = None
    records[source_name] = record


def record_failure(
    records: Dict[str, SourceHealthRecord],
    source_name: str,
    error: str,
    http_code: Optional[int] = None,
    item_count: int = 0,
) -> None:
    now = utc_now_iso()
    record = records.get(source_name, SourceHealthRecord(source_name=source_name))
    record.last_attempt_at = now
    record.last_status = "failed"
    record.last_http_code = http_code
    record.consecutive_failures += 1
    record.item_count = item_count
    record.last_error = error
    records[source_name] = record


def record_partial_success(
    records: Dict[str, SourceHealthRecord],
    source_name: str,
    error: str,
    item_count: int,
    http_code: Optional[int] = None,
) -> None:
    now = utc_now_iso()
    record = records.get(source_name, SourceHealthRecord(source_name=source_name))
    record.last_attempt_at = now
    record.last_success_at = now
    record.last_status = "partial"
    record.last_http_code = http_code
    record.consecutive_failures += 1
    record.item_count = item_count
    record.last_error = error
    records[source_name] = record


def degraded_sources(records: Dict[str, SourceHealthRecord]) -> Dict[str, SourceHealthRecord]:
    return {
        name: record
        for name, record in records.items()
        if record.last_status != "success" or record.consecutive_failures > 0
    }
