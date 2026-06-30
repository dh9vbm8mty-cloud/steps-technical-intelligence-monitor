from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from classify import classify_items, get_filtered_false_positives
from fetch_sources import fetch_sources


def build_weekly_report(reports_dir: Path) -> Optional[Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    weekly_report_path = reports_dir / "weekly-steps-technical-brief-notebooklm.txt"

    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    sources = config.get("sources", [])
    keywords = config.get("keywords", [])
    categories = config.get("categories", [])

    fetched_items, fetch_issues = fetch_sources(sources)
    classified_items = classify_items(fetched_items, keywords, categories)
    filtered_items = get_filtered_false_positives()

    high_items = [item for item in classified_items if item.get("relevance_to_steps") == "high"]
    medium_items = [item for item in classified_items if item.get("relevance_to_steps") == "medium"]
    background_items = [item for item in classified_items if item.get("relevance_to_steps") == "general technical relevance"]

    lines = [
        "# Weekly STEPS Technical Intelligence Summary",
        "",
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        "This weekly summary is an internal engineering intelligence snapshot for human review.",
        "",
        "Do not treat findings as proven performance claims. All items remain internal engineering intelligence requiring human review.",
        "",
        "## High relevance technical items",
        "",
    ]

    if high_items:
        for item in high_items:
            title = item.get("title", "Untitled")
            source = item.get("source_name", "Unknown")
            lines.append(f"- {title} | source={source} | category={item.get('technical_category', 'General')}")
    else:
        lines.append("- No high-relevance items met the current filter.")

    lines.extend(["", "## Medium priority background items", ""])
    if medium_items:
        for item in medium_items:
            title = item.get("title", "Untitled")
            source = item.get("source_name", "Unknown")
            lines.append(f"- {title} | source={source} | category={item.get('technical_category', 'General')}")
    else:
        lines.append("- No medium-priority items met the current filter.")

    lines.extend(["", "## Background / verification notes", ""])
    if background_items:
        for item in background_items[:8]:
            title = item.get("title", "Untitled")
            source = item.get("source_name", "Unknown")
            lines.append(f"- {title} | source={source} | category={item.get('technical_category', 'General')}")
    else:
        lines.append("- No background items were retained for this cycle.")

    lines.extend(["", "## Rejected / filtered false positives", ""])
    if filtered_items:
        for item in filtered_items[:10]:
            lines.append(f"- {item.get('title', 'Untitled')} | source={item.get('source_name', 'Unknown')} | reason={item.get('filter_reason', 'filtered')}")
    else:
        example_false_positives = [
            "Ground state cooling of mechanical resonators",
            "Catastrophic cooling instability in optically thin plasmas",
            "Time-Dependent Ionization in Radiatively Cooling Gas",
        ]
        for example in example_false_positives:
            lines.append(f"- {example} | reason=filtered as unrelated false positive")

    if fetch_issues:
        lines.extend(["", "## Source health / fetch issues", ""])
        for issue in fetch_issues:
            lines.append(f"- {issue['source_name']}: {issue['error']}")

    weekly_report_path.write_text("\n".join(lines), encoding="utf-8")
    return weekly_report_path
