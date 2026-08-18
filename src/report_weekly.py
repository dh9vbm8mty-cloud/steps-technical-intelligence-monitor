from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


DEGRADED_WARNING = "Monitoring coverage is degraded; absence of findings is inconclusive for affected source domains."


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def generate_weekly_reports(project_root: Path) -> List[Path]:
    settings = load_yaml(project_root / "config" / "settings.yaml")
    runs_dir = project_root / settings["registry"]["runs_dir"]
    reports_dir = project_root / settings["reports"]["weekly_dir"]
    reports_dir.mkdir(parents=True, exist_ok=True)
    runs = load_recent_runs(runs_dir, days=7)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    markdown_path = reports_dir / f"{today}-{settings['reports']['weekly_slug']}.md"
    notebooklm_path = reports_dir / f"{settings['reports']['weekly_slug']}-notebooklm.txt"
    markdown_path.write_text(build_weekly_markdown(runs, settings), encoding="utf-8")
    notebooklm_path.write_text(build_weekly_notebooklm(runs, settings), encoding="utf-8")
    return [markdown_path, notebooklm_path]


def load_recent_runs(runs_dir: Path, days: int = 7) -> List[Dict[str, Any]]:
    if not runs_dir.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    runs = []
    for path in sorted(runs_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        timestamp = parse_timestamp(payload.get("run_timestamp"))
        if timestamp and timestamp >= cutoff:
            runs.append(payload)
    return runs


def parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def build_weekly_markdown(runs: List[Dict[str, Any]], settings: Dict[str, Any]) -> str:
    aggregate = aggregate_runs(runs)
    lines = [
        f"# {settings['project']['name']} Weekly Brief",
        "",
        "## Internal Review Warning",
        settings["project"]["disclaimer"],
        "",
        "## Weekly Executive Judgment",
        weekly_judgment(aggregate),
        "",
        "## Number of Genuinely New Items",
        f"- {len(aggregate['new_items'])}",
        "",
        "## Number of Materially Updated Items",
        f"- {len(aggregate['updated_items'])}",
        "",
        "## Critical / High Findings",
    ]
    append_dict_items(lines, aggregate["critical_high"])
    lines.append("")
    lines.append("## Research Findings")
    append_dict_items(lines, aggregate["research"])
    lines.append("")
    lines.append("## Field / Demonstration / Operational Projects")
    append_dict_items(lines, aggregate["field_projects"])
    lines.append("")
    lines.append("## Alternative / Competing Technologies")
    append_dict_items(lines, aggregate["alternatives"])
    lines.append("")
    lines.append("## Validation / Measurement Lessons")
    append_lessons(lines, aggregate["all_items"], {"field validation", "sensor / instrumentation", "heat flux"})
    lines.append("")
    lines.append("## Construction / Durability / Maintenance Lessons")
    append_lessons(lines, aggregate["all_items"], {"construction", "durability", "maintenance"})
    lines.append("")
    lines.append("## Controls / Sensors / Energy Lessons")
    append_lessons(lines, aggregate["all_items"], {"control strategy", "sensor / instrumentation", "pumping / energy consumption"})
    lines.append("")
    lines.append("## Commercial Signals")
    append_dict_items(lines, aggregate["commercial"])
    lines.append("")
    lines.append("## Patent Review Triggers")
    append_dict_items(lines, aggregate["patents"])
    lines.append("")
    lines.append("## Source Health / Coverage Limitations")
    append_source_limitations(lines, aggregate)
    lines.append("")
    lines.append("## Human Review Queue")
    append_dict_items(lines, aggregate["review_queue"])
    lines.append("")
    lines.append("## Long-Term Knowledge Base Updates")
    lines.append(f"- Registry received {len(aggregate['new_items'])} genuinely new items and {len(aggregate['updated_items'])} materially updated known items during the previous seven days.")
    return "\n".join(lines)


def build_weekly_notebooklm(runs: List[Dict[str, Any]], settings: Dict[str, Any]) -> str:
    aggregate = aggregate_runs(runs)
    lines = [
        f"Project: {settings['project']['name']}",
        f"Internal Review Warning: {settings['project']['disclaimer']}",
        "",
        f"Weekly new items: {len(aggregate['new_items'])}",
        f"Weekly updated items: {len(aggregate['updated_items'])}",
        f"Major source failures present: {aggregate['has_source_failures']}",
        "",
        "Critical / High Findings:",
    ]
    append_dict_items(lines, aggregate["critical_high"])
    lines.append("")
    lines.append("Human Review Queue:")
    append_dict_items(lines, aggregate["review_queue"])
    lines.append("")
    lines.append("Coverage Limitations:")
    append_source_limitations(lines, aggregate)
    return "\n".join(lines)


def aggregate_runs(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    all_items = []
    degraded = []
    for run in runs:
        all_items.extend(run.get("new_items", []))
        all_items.extend(run.get("updated_items", []))
        degraded.extend(run.get("degraded_sources", []))
    new_items = [item for run in runs for item in run.get("new_items", [])]
    updated_items = [item for run in runs for item in run.get("updated_items", [])]
    return {
        "all_items": all_items,
        "new_items": new_items,
        "updated_items": updated_items,
        "critical_high": [item for item in all_items if item.get("relevance") in {"Critical", "High"}],
        "research": [item for item in all_items if item.get("item_type") in {"Research Paper", "Review Paper", "Laboratory Study"}],
        "field_projects": [item for item in all_items if item.get("project_maturity") in {"Outdoor Experimental Section", "Pilot", "Demonstration", "Operational Infrastructure"}],
        "alternatives": [item for item in all_items if item.get("alternative_or_competitor_relevance") == "Reported"],
        "commercial": [item for item in all_items if item.get("project_maturity") == "Commercial Product / Deployment" or item.get("item_type") in {"Commercial Deployment", "Company / Product"}],
        "patents": [item for item in all_items if item.get("patent_review_trigger")],
        "review_queue": [item for item in all_items if item.get("human_review_required") and item.get("relevance") != "Reject"],
        "degraded_sources": degraded,
        "has_source_failures": bool(degraded),
    }


def weekly_judgment(aggregate: Dict[str, Any]) -> str:
    if aggregate["has_source_failures"] and not aggregate["critical_high"]:
        return DEGRADED_WARNING
    if aggregate["critical_high"]:
        return "Critical / High STEPS engineering intelligence was retained for human review."
    if aggregate["new_items"] or aggregate["updated_items"]:
        return "No Critical / High item was retained, but lower-priority STEPS technical intelligence changed during the period."
    return "No new retained STEPS technical intelligence was identified from saved source history."


def append_dict_items(lines: List[str], items: List[Dict[str, Any]]) -> None:
    if not items:
        lines.append("- None identified from saved history.")
        return
    for item in items[:50]:
        families = ", ".join(item.get("technology_families") or []) or "not reported"
        lines.append(
            f"- {item.get('title', 'Untitled')} | relevance={item.get('relevance', 'Unknown')} | status={item.get('status', 'Unknown')} | type={item.get('item_type', 'Unknown')} | source={item.get('source_name', 'Unknown')} | year={item.get('year') or 'not reported'} | families={families} | url={item.get('canonical_url') or 'not reported'}"
        )


def append_lessons(lines: List[str], items: List[Dict[str, Any]], tags: set[str]) -> None:
    matched = [item for item in items if tags.intersection(set(item.get("engineering_relevance_tags") or []))]
    if not matched:
        lines.append("- No lesson can be stated from reported metadata alone.")
        return
    append_dict_items(lines, matched)


def append_source_limitations(lines: List[str], aggregate: Dict[str, Any]) -> None:
    if not aggregate["degraded_sources"]:
        lines.append("- No degraded source coverage recorded in saved runs.")
        return
    lines.append(f"- {DEGRADED_WARNING}")
    for source in aggregate["degraded_sources"][:25]:
        lines.append(
            f"- {source.get('source_name', 'Unknown')}: status={source.get('last_status', 'Unknown')}; consecutive_failures={source.get('consecutive_failures', 0)}; error={source.get('last_error') or 'none'}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    for path in generate_weekly_reports(Path(args.root)):
        print(path)


if __name__ == "__main__":
    main()
