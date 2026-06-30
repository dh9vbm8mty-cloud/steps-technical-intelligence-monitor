from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple


def generate_daily_reports(
    items: List[Dict[str, Any]],
    fetch_issues: List[Dict[str, Any]],
    config: Dict[str, Any],
    reports_dir: Path,
) -> List[Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    markdown_path = reports_dir / f"{today}-steps-technical-brief.md"
    notebooklm_path = reports_dir / f"{today}-steps-technical-brief-notebooklm.txt"

    markdown_content = build_markdown_report(items, fetch_issues, config)
    notebooklm_content = build_notebooklm_report(items, fetch_issues, config)

    markdown_path.write_text(markdown_content, encoding="utf-8")
    notebooklm_path.write_text(notebooklm_content, encoding="utf-8")

    return [markdown_path, notebooklm_path]


def build_markdown_report(
    items: List[Dict[str, Any]],
    fetch_issues: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> str:
    lines = [
        "# STEPS Technical Intelligence Brief",
        "",
        "This document is internal engineering intelligence for human review only.",
        "It should not be treated as a verified performance claim.",
        "",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Project: {config.get('project', {}).get('name', 'STEPS Technical Intelligence Monitor')}",
        "",
        "## Monitoring focus",
        "- Pavement cooling and urban heat mitigation",
        "- Thermal energy pavement and heat harvesting",
        "- RTSU and system-engineering relevance",
        "- Measurement, validation, and test methods",
        "- Alternative and competing solutions",
        "- Patent and novelty watch",
        "",
        "## Source health / fetch issues",
    ]

    if fetch_issues:
        for issue in fetch_issues:
            lines.append(f"- {issue['source_name']}: {issue['error']}")
    else:
        lines.append("- No source fetch issues recorded.")

    lines.extend(["", "## Findings", ""])
    if not items:
        lines.append("No matching items were identified in this run.")
        return "\n".join(lines)

    for item in items:
        title = item.get("title", "Untitled")
        link = item.get("link", "")
        lines.append(f"### {title}")
        lines.append(f"- Source: {item.get('source_name', 'Unknown')} ({item.get('source_category', 'unknown')})")
        lines.append(f"- Technical category: {item.get('technical_category', 'General')}")
        lines.append(f"- Relevance to STEPS: {item.get('relevance_to_steps', 'unknown')}")
        lines.append(f"- Technical risk/opportunity: {item.get('technical_risk_or_opportunity', 'n/a')}")
        lines.append(f"- Validation implication: {item.get('validation_implication', 'n/a')}")
        lines.append(f"- Competitor or alternative implication: {item.get('competitor_or_alternative_implication', 'n/a')}")
        lines.append(f"- Patent or novelty implication: {item.get('patent_or_novelty_implication', 'n/a')}")
        lines.append(f"- Recommended action: {item.get('recommended_action', 'n/a')}")
        lines.append(f"- Link: {link}")
        lines.append("")

    return "\n".join(lines)


def build_notebooklm_report(
    items: List[Dict[str, Any]],
    fetch_issues: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> str:
    lines = [
        f"Project: {config.get('project', {}).get('name', 'STEPS Technical Intelligence Monitor')}",
        f"Disclaimer: {config.get('project', {}).get('disclaimer', 'Internal engineering intelligence for human review only')}",
        "",
        "Source health / fetch issues:",
    ]

    if fetch_issues:
        for issue in fetch_issues:
            lines.append(f"- {issue['source_name']}: {issue['error']}")
    else:
        lines.append("- No source fetch issues recorded.")

    lines.extend(["", "Findings:"])
    if not items:
        lines.append("No matching items were identified in this run.")
        return "\n".join(lines)

    for item in items:
        lines.append(
            f"- {item.get('title', 'Untitled')} | source={item.get('source_name', 'Unknown')} | category={item.get('technical_category', 'General')} | relevance={item.get('relevance_to_steps', 'unknown')}"
        )

    return "\n".join(lines)
