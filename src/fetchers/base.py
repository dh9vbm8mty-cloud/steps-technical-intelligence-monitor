from __future__ import annotations

import time
from email.utils import parsedate_to_datetime
from typing import Any, Dict, List, Optional, Tuple

import requests

from models import RawItem


RETRY_HTTP_CODES = {429, 502, 503, 504}


class FetchResult:
    def __init__(self, items: Optional[List[RawItem]] = None, error: Optional[str] = None, http_code: Optional[int] = None) -> None:
        self.items = items or []
        self.error = error
        self.http_code = http_code


def request_with_retry(source: Dict[str, Any], params: Optional[Dict[str, Any]] = None) -> Tuple[Optional[requests.Response], Optional[str], Optional[int]]:
    url = source.get("url") or source.get("base_url")
    timeout = int(source.get("timeout", 20))
    retries = int(source.get("retries", 2))
    backoff = float(source.get("backoff_seconds", 2))
    headers = {"User-Agent": "HENGYUN STEPS technical intelligence monitor/1.0"}

    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, timeout=timeout, headers=headers)
            if response.status_code in RETRY_HTTP_CODES and attempt < retries:
                sleep_for = retry_after_seconds(response) or backoff * (2 ** attempt)
                time.sleep(min(sleep_for, 30))
                continue
            response.raise_for_status()
            return response, None, response.status_code
        except requests.RequestException as exc:
            http_code = getattr(getattr(exc, "response", None), "status_code", None)
            if http_code is None and "429" in str(exc):
                http_code = 429
            if attempt < retries and http_code in RETRY_HTTP_CODES:
                time.sleep(min(backoff * (2 ** attempt), 30))
                continue
            return None, str(exc), http_code
    return None, "unknown request failure", None


def retry_after_seconds(response: requests.Response) -> Optional[float]:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    if value.isdigit():
        return float(value)
    try:
        retry_at = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return max((retry_at.timestamp() - time.time()), 0)


def maybe_sleep(source: Dict[str, Any]) -> None:
    interval = float(source.get("request_interval_seconds", 0) or 0)
    if interval > 0:
        time.sleep(interval)
