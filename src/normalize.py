from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from models import IntelligenceItem, RawItem


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def normalize_title(title: str) -> str:
    cleaned = title.lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return " ".join(cleaned.split())


def normalize_doi(doi: Optional[str]) -> Optional[str]:
    if not doi:
        return None
    value = doi.strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = value.removeprefix("doi:")
    return value.strip() or None


def canonicalize_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    parts = urlsplit(url.strip())
    scheme = parts.scheme.lower() or "https"
    netloc = parts.netloc.lower()
    path = re.sub(r"/+$", "", parts.path)
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
    ]
    query = urlencode(filtered_query)
    return urlunsplit((scheme, netloc, path, query, ""))


def normalize_patent_number(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = re.sub(r"[^a-zA-Z0-9]", "", value).upper()
    return normalized or None


def make_internal_id(*signals: Optional[str]) -> str:
    basis = "|".join(signal for signal in signals if signal)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def normalize_raw_item(raw: RawItem, discovered_at: Optional[str] = None) -> IntelligenceItem:
    timestamp = discovered_at or utc_now_iso()
    doi = normalize_doi(raw.doi)
    patent_number = normalize_patent_number(raw.patent_publication_number)
    canonical_url = canonicalize_url(raw.canonical_url or raw.source_url)
    normalized_title = normalize_title(raw.title)
    internal_id = make_internal_id(
        doi,
        patent_number,
        canonical_url,
        normalized_title,
        raw.organization,
        str(raw.year or ""),
    )
    return IntelligenceItem(
        internal_id=internal_id,
        item_type=raw.item_type,
        title=raw.title.strip(),
        normalized_title=normalized_title,
        source_name=raw.source_name,
        source_url=raw.source_url,
        canonical_url=canonical_url,
        DOI=doi,
        patent_publication_number=patent_number,
        authors=raw.authors,
        organization=raw.organization,
        country=raw.country,
        location=raw.location,
        year=raw.year,
        publication=raw.publication,
        abstract_or_summary=raw.abstract_or_summary,
        discovered_at=timestamp,
        last_seen_at=timestamp,
        status="NEW",
        raw_source_reference=raw.raw_source_reference,
    )
