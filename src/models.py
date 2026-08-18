from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


UNKNOWN = "Unknown"
NOT_REPORTED = "Not Reported"


@dataclass
class RawItem:
    source_name: str
    source_url: str
    item_type: str
    title: str
    canonical_url: Optional[str] = None
    doi: Optional[str] = None
    patent_publication_number: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    organization: Optional[str] = None
    country: Optional[str] = None
    location: Optional[str] = None
    year: Optional[int] = None
    publication: Optional[str] = None
    abstract_or_summary: Optional[str] = None
    raw_source_reference: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligenceItem:
    internal_id: str
    item_type: str
    title: str
    normalized_title: str
    source_name: str
    source_url: str
    canonical_url: Optional[str]
    DOI: Optional[str]
    patent_publication_number: Optional[str]
    authors: List[str]
    organization: Optional[str]
    country: Optional[str]
    location: Optional[str]
    year: Optional[int]
    publication: Optional[str]
    abstract_or_summary: Optional[str]
    discovered_at: str
    last_seen_at: str
    status: str
    relevance: str = UNKNOWN
    technology_families: List[str] = field(default_factory=list)
    project_maturity: str = UNKNOWN
    validation_quality: str = UNKNOWN
    engineering_relevance_tags: List[str] = field(default_factory=list)
    alternative_or_competitor_relevance: str = UNKNOWN
    patent_review_trigger: bool = False
    human_review_required: bool = True
    source_confidence: str = UNKNOWN
    raw_source_reference: Dict[str, Any] = field(default_factory=dict)
    duplicate_of: Optional[str] = None
    update_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceHealthRecord:
    source_name: str
    last_attempt_at: Optional[str] = None
    last_success_at: Optional[str] = None
    last_status: str = UNKNOWN
    last_http_code: Optional[int] = None
    consecutive_failures: int = 0
    item_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
