from typing import Optional

from classify import classify_items
from models import IntelligenceItem


TAXONOMY = {
    "classification": {
        "domain_terms": ["pavement", "asphalt", "road surface"],
        "thermal_terms": ["thermal", "temperature", "cooling", "heat", "heat flux"],
        "unrelated_false_positive_terms": ["plasma", "electronics cooling"],
        "explicit_review_triggers": ["field", "demonstration", "validation", "construction", "sensor"],
        "technology_families": {
            "Passive Reflective": ["reflective pavement", "high albedo"],
            "Construction / Durability": ["construction", "durability"],
            "Measurement / Validation": ["validation", "field test", "heat flux"],
            "Embedded Sensors / Monitoring": ["sensor", "monitoring"],
        },
    }
}


def make_item(title: str, abstract: Optional[str] = None) -> IntelligenceItem:
    return IntelligenceItem(
        internal_id="id",
        item_type="Research Paper",
        title=title,
        normalized_title=title.lower(),
        source_name="OpenAlex",
        source_url="https://example.test",
        canonical_url=None,
        DOI=None,
        patent_publication_number=None,
        authors=[],
        organization=None,
        country=None,
        location=None,
        year=None,
        publication=None,
        abstract_or_summary=abstract,
        discovered_at="2026-01-01T00:00:00Z",
        last_seen_at="2026-01-01T00:00:00Z",
        status="NEW",
    )


def test_passive_cooling_alternative_retained() -> None:
    item = classify_items([make_item("High albedo reflective pavement cooling")], TAXONOMY)[0]
    assert item.relevance == "Medium"
    assert "Passive Reflective" in item.technology_families
    assert item.status == "NEW"


def test_unrelated_cooling_rejected() -> None:
    item = classify_items([make_item("Plasma cooling model")], TAXONOMY)[0]
    assert item.relevance == "Reject"
    assert item.status == "REJECTED"


def test_construction_cooling_classified_appropriately() -> None:
    item = classify_items([make_item("Asphalt pavement construction cooling temperature control")], TAXONOMY)[0]
    assert item.relevance == "High"
    assert "construction" in item.engineering_relevance_tags


def test_critical_requires_stronger_evidence_than_keyword_count() -> None:
    many_keywords = make_item("Pavement thermal cooling temperature heat road surface asphalt")
    critical = make_item("Full-scale field demonstration of pavement heat flux measurement")
    result = classify_items([many_keywords, critical], TAXONOMY)
    assert result[0].relevance == "Medium"
    assert result[1].relevance == "Critical"


def test_background_items_excluded_from_default_review_queue() -> None:
    item = classify_items([make_item("Generic sensor monitoring platform")], TAXONOMY)[0]
    assert item.relevance == "Background"
    assert item.human_review_required is False
