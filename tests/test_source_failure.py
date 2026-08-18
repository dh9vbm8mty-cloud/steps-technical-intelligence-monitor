import json
from pathlib import Path

import fetchers.base as base
from fetchers.base import FetchResult, request_with_retry
from main import update_health
from source_health import load_source_health, save_source_health


class Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        self.headers = {"Retry-After": "0"}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            import requests

            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error


def test_source_failure_does_not_terminate_run() -> None:
    records = {}
    update_health(records, "Broken Source", FetchResult([], "HTTP 503", 503))
    assert records["Broken Source"].last_status == "failed"
    assert records["Broken Source"].consecutive_failures == 1


def test_retry_logic_handles_429(monkeypatch) -> None:
    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        return Response(429 if calls["count"] == 1 else 200)

    monkeypatch.setattr(base.requests, "get", fake_get)
    monkeypatch.setattr(base.time, "sleep", lambda seconds: None)
    response, error, http_code = request_with_retry({"url": "https://example.test", "retries": 1, "backoff_seconds": 0})
    assert response is not None
    assert error is None
    assert http_code == 200
    assert calls["count"] == 2


def test_source_health_persistence(tmp_path: Path) -> None:
    path = tmp_path / "source_health.json"
    records = {}
    update_health(records, "Crossref", FetchResult([], "HTTP 503", 503))
    save_source_health(path, records)
    assert json.loads(path.read_text(encoding="utf-8"))["Crossref"]["last_status"] == "failed"
    assert load_source_health(path)["Crossref"].consecutive_failures == 1
