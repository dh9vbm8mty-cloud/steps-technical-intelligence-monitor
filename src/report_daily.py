from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from models import IntelligenceItem, SourceHealthRecord
from source_health import degraded_sources


DEGRADED_WARNING = "Monitoring coverage is degraded; absence of findings is inconclusive for affected source domains."


def generate_daily_reports(
    items: List[IntelligenceItem],
    run_summary: Dict[str, Any],
    source_health: Dict[str, SourceHealthRecord],
    settings: Dict[str, Any],
    project_root: Path,
) -> List[Path]:
    reports_dir = project_root / settings["reports"]["daily_dir"]
    reports_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    markdown_path = reports_dir / f"{today}-{settings['reports']['daily_slug']}.md"
    notebooklm_path = reports_dir / f"{today}-{settings['reports']['daily_slug']}-notebooklm.txt"
    markdown_path.write_text(build_daily_markdown(items, run_summary, source_health, settings), encoding="utf-8")
    notebooklm_path.write_text(build_daily_notebooklm(items, run_summary, source_health, settings), encoding="utf-8")
    return [markdown_path, notebooklm_path]


def build_daily_markdown(
    items: List[IntelligenceItem],
    run_summary: Dict[str, Any],
    source_health: Dict[str, SourceHealthRecord],
    settings: Dict[str, Any],
) -> str:
    retained = [item for item in items if item.relevance != "Reject"]
    lines = [
        f"# {settings['project']['name']} Daily Brief",
        "",
        "## Internal Review Warning",
        settings["project"]["disclaimer"],
        "",
        "## Daily Executive Judgment",
        daily_judgment(items, source_health),
        "",
        "## Run Counts",
        f"- Raw items: {run_summary['raw_item_count']}",
        f"- Normalized items: {run_summary['normalized_item_count']}",
        f"- NEW: {run_summary['new_item_count']}",
        f"- UPDATED: {run_summary['updated_item_count']}",
        f"- DUPLICATE / PREVIOUSLY_SEEN: {run_summary['duplicate_item_count']}",
        f"- REJECTED: {run_summary['rejected_item_count']}",
        "",
        "## New Critical / High Findings",
    ]
    append_items(lines, [item for item in retained if item.status == "NEW" and item.relevance in {"Critical", "High"}])
    lines.append("")
    lines.append("## New Technical Research")
    append_items(lines, [item for item in retained if item.status == "NEW" and item.item_type in {"Research Paper", "Review Paper", "Laboratory Study"}])
    lines.append("")
    lines.append("## Field / Demonstration / Operational Signals")
    append_items(lines, [item for item in retained if item.status == "NEW" and item.project_maturity in {"Outdoor Experimental Section", "Pilot", "Demonstration", "Operational Infrastructure"}])
    lines.append("")
    lines.append("## Alternative / Competing Solutions")
    append_items(lines, [item for item in retained if item.status == "NEW" and item.alternative_or_competitor_relevance == "Reported"])
    lines.append("")
    lines.append("## Validation / Measurement Findings")
    append_items(lines, [item for item in retained if item.status == "NEW" and has_tag(item, {"field validation", "sensor / instrumentation", "heat flux"})])
    lines.append("")
    lines.append("## Construction / Durability / Maintenance Findings")
    append_items(lines, [item for item in retained if item.status == "NEW" and has_tag(item, {"construction", "durability", "maintenance"})])
    lines.append("")
    lines.append("## Controls / Sensors / Energy Findings")
    append_items(lines, [item for item in retained if item.status == "NEW" and has_tag(item, {"control strategy", "sensor / instrumentation", "pumping / energy consumption"})])
    lines.append("")
    lines.append("## Updated Known Items")
    append_items(lines, [item for item in retained if item.status == "UPDATED"])
    lines.append("")
    lines.append("## Patent Review Triggers")
    append_items(lines, [item for item in retained if item.patent_review_trigger])
    lines.append("")
    lines.append("## Rejected False Positives")
    append_items(lines, [item for item in items if item.status == "REJECTED"])
    lines.append("")
    lines.append("## Source Health")
    append_source_health(lines, source_health)
    lines.append("")
    lines.append("## Human Review Queue")
    append_items(lines, [item for item in retained if item.human_review_required and item.status in {"NEW", "UPDATED"}])
    return "\n".join(lines)


def build_daily_notebooklm(
    items: List[IntelligenceItem],
    run_summary: Dict[str, Any],
    source_health: Dict[str, SourceHealthRecord],
    settings: Dict[str, Any],
) -> str:
    lines = [
        f"Project: {settings['project']['name']}",
        f"Internal Review Warning: {settings['project']['disclaimer']}",
        "",
        f"Daily judgment: {daily_judgment(items, source_health)}",
        f"Counts: NEW={run_summary['new_item_count']}; UPDATED={run_summary['updated_item_count']}; DUPLICATE_OR_SEEN={run_summary['duplicate_item_count']}; REJECTED={run_summary['rejected_item_count']}",
        "",
        "Human Review Queue:",
    ]
    append_items(lines, [item for item in items if item.human_review_required and item.status in {"NEW", "UPDATED"}])
    lines.append("")
    lines.append("Source Health:")
    append_source_health(lines, source_health)
    return "\n".join(lines)


def daily_judgment(items: List[IntelligenceItem], source_health: Dict[str, SourceHealthRecord]) -> str:
    retained = [item for item in items if item.relevance != "Reject" and item.status in {"NEW", "UPDATED"}]
    if degraded_sources(source_health) and not retained:
        return DEGRADED_WARNING
    if any(item.relevance == "Critical" for item in retained):
        return "Critical STEPS engineering intelligence was retained for human review."
    if any(item.relevance == "High" for item in retained):
        return "High-relevance STEPS engineering intelligence was retained for human review."
    if retained:
        return "No Critical / High item was retained, but lower-priority technical intelligence was added or updated."
    return "No new retained STEPS technical intelligence was identified from available source coverage."


def append_items(lines: List[str], items: List[IntelligenceItem]) -> None:
    if not items:
        lines.append("- None identified.")
        return
    for item in items[:50]:
        lines.append(
            f"- {item.title} | relevance={item.relevance} | status={item.status} | type={item.item_type} | source={item.source_name} | year={item.year or 'not reported'} | families={', '.join(item.technology_families) or 'not reported'} | url={item.canonical_url or 'not reported'}"
        )


def append_source_health(lines: List[str], source_health: Dict[str, SourceHealthRecord]) -> None:
    degraded = degraded_sources(source_health)
    if degraded:
        lines.append(f"- {DEGRADED_WARNING}")
    for name, record in sorted(source_health.items()):
        lines.append(
            f"- {name}: status={record.last_status}; consecutive_failures={record.consecutive_failures}; items={record.item_count}; http={record.last_http_code or 'n/a'}; error={record.last_error or 'none'}"
        )


def has_tag(item: IntelligenceItem, tags: set[str]) -> bool:
    return bool(tags.intersection(item.engineering_relevance_tags))
