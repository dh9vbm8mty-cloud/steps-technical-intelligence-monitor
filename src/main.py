from pathlib import Path

import yaml

from classify import classify_items
from fetch_sources import fetch_sources
from report import generate_daily_reports
from weekly_report import build_weekly_report


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    config_path = project_root / "config.yaml"
    reports_dir = project_root / "reports"

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    sources = config.get("sources", [])
    keywords = config.get("keywords", [])
    categories = config.get("categories", [])

    fetched_items, fetch_issues = fetch_sources(sources)
    classified_items = classify_items(fetched_items, keywords, categories)
    generated_files = generate_daily_reports(classified_items, fetch_issues, config, reports_dir)
    weekly_report_path = build_weekly_report(reports_dir)

    print("Generated report files:")
    for path in generated_files:
        print(f"- {path}")

    if weekly_report_path:
        print(f"- {weekly_report_path}")

    if fetch_issues:
        print("Fetch issues:")
        for issue in fetch_issues:
            print(f"- {issue['source_name']}: {issue['error']}")


if __name__ == "__main__":
    main()
