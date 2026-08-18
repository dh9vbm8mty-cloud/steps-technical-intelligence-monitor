import json
from pathlib import Path

import report_weekly
from report_weekly import generate_weekly_reports


def write_settings(root: Path) -> None:
    (root / "config").mkdir()
    (root / "data" / "runs").mkdir(parents=True)
    (root / "config" / "settings.yaml").write_text(
        """
project:
  name: Test STEPS Monitor
  disclaimer: Internal only.
registry:
  runs_dir: data/runs
reports:
  weekly_dir: reports/weekly
  weekly_slug: weekly-steps-technical-brief
""",
        encoding="utf-8",
    )


def test_weekly_aggregates_saved_history(tmp_path: Path) -> None:
    write_settings(tmp_path)
    run = {
        "run_timestamp": "2099-01-01T00:00:00Z",
        "new_items": [
            {
                "title": "Full-scale field demonstration of pavement thermal monitoring",
                "relevance": "Critical",
                "status": "NEW",
                "item_type": "Research Paper",
                "source_name": "OpenAlex",
                "year": 2024,
                "canonical_url": "https://example.test",
                "technology_families": ["Measurement / Validation"],
                "engineering_relevance_tags": ["field validation", "sensor / instrumentation"],
                "human_review_required": True,
            }
        ],
        "updated_items": [],
        "degraded_sources": [],
    }
    (tmp_path / "data" / "runs" / "run.json").write_text(json.dumps(run), encoding="utf-8")
    paths = generate_weekly_reports(tmp_path)
    assert len(paths) == 2
    assert "Full-scale field demonstration" in paths[0].read_text(encoding="utf-8")


def test_weekly_does_not_refetch(monkeypatch, tmp_path: Path) -> None:
    write_settings(tmp_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("weekly report must not refetch")

    monkeypatch.setattr(report_weekly, "load_recent_runs", lambda runs_dir, days=7: [])
    monkeypatch.setattr("fetchers.crossref.fetch_crossref", fail_if_called)
    generate_weekly_reports(tmp_path)
