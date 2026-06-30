from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup


def fetch_sources(sources: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    items: List[Dict[str, Any]] = []
    issues: List[Dict[str, Any]] = []

    for source in sources:
        url = source.get("url")
        if not url:
            continue

        try:
            response = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code in {403, 404}:
                raise requests.HTTPError(f"HTTP {response.status_code}")
            response.raise_for_status()
        except requests.RequestException as exc:
            issues.append({
                "source_name": source.get("name", "Unknown"),
                "url": url,
                "error": str(exc),
            })
            continue

        content_type = response.headers.get("content-type", "").lower()
        text = response.text.strip()
        if "json" in content_type or text.startswith("{") or text.startswith("["):
            parsed_items = parse_json(text)
        elif "xml" in content_type or text.lstrip().startswith("<?xml"):
            parsed_items = parse_feed(response.text)
        else:
            parsed_items = parse_html(response.text)

        for item in parsed_items:
            item_payload = {
                "source_name": source.get("name", "Unknown"),
                "source_type": source.get("type", "unknown"),
                "source_url": url,
                **item,
            }
            items.append(item_payload)

    return items, issues


def parse_feed(content: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(content, "html.parser")
    entries: List[Dict[str, Any]] = []
    for entry in soup.find_all(["item", "entry"]):
        title = get_text(entry, ["title", "name"])
        link = get_link(entry)
        entries.append({"title": title.strip(), "link": link.strip()})
    return entries


def parse_html(content: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(content, "html.parser")
    links: List[Dict[str, Any]] = []
    for anchor in soup.find_all("a", href=True)[:12]:
        title = " ".join(anchor.get_text(" ", strip=True).split())
        link = anchor["href"]
        if title:
            links.append({"title": title, "link": link})
    return links


def parse_json(content: str) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return []

    items: List[Dict[str, Any]] = []

    if isinstance(payload, dict):
        if isinstance(payload.get("data"), list):
            candidates = payload["data"]
        elif isinstance(payload.get("message"), dict):
            message = payload["message"]
            if isinstance(message.get("items"), list):
                candidates = message["items"]
            else:
                candidates = []
        else:
            candidates = []
    else:
        candidates = payload if isinstance(payload, list) else []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        title = normalize_text_value(candidate.get("title"))
        summary = normalize_text_value(candidate.get("summary") or candidate.get("abstract") or candidate.get("description"))
        link = candidate.get("url") or candidate.get("URL") or ""
        if title:
            item_payload = {"title": title, "link": str(link)}
            if summary:
                item_payload["summary"] = summary
            items.append(item_payload)

    return items


def normalize_text_value(value: Any) -> str:
    if isinstance(value, list):
        for entry in value:
            normalized = normalize_text_value(entry)
            if normalized:
                return normalized
        return ""

    if isinstance(value, dict):
        for key in ("text", "title", "value", "abstract"):
            if key in value:
                normalized = normalize_text_value(value[key])
                if normalized:
                    return normalized
        return ""

    if isinstance(value, str):
        return value.strip()

    return ""


def get_text(tag: Any, names: List[str]) -> str:
    for name in names:
        element = tag.find(name)
        if element is not None and element.get_text(strip=True):
            return element.get_text(strip=True)
    return ""


def get_link(tag: Any) -> str:
    link = tag.find("link")
    if link is None:
        return ""
    if link.get("href"):
        return link.get("href")
    return link.get_text(strip=True)
