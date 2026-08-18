from typing import Optional

from dedup import apply_dedup
from models import IntelligenceItem


def make_item(
    title: str,
    doi: Optional[str] = None,
    url: Optional[str] = None,
    abstract: Optional[str] = None,
) -> IntelligenceItem:
    return IntelligenceItem(
        internal_id=title.lower().replace(" ", "-"),
        item_type="Research Paper",
        title=title,
        normalized_title=title.lower(),
        source_name="Crossref",
        source_url="https://example.test/source",
        canonical_url=url,
        DOI=doi,
        patent_publication_number=None,
        authors=[],
        organization=None,
        country=None,
        location=None,
        year=2024,
        publication=None,
        abstract_or_summary=abstract,
        discovered_at="2026-01-01T00:00:00Z",
        last_seen_at="2026-01-01T00:00:00Z",
        status="NEW",
        relevance="Medium",
    )


def test_doi_dedup_marks_previously_seen() -> None:
    seen = {"items": {}, "index": {}}
    first = apply_dedup([make_item("A", doi="10.1/a")], seen)[0]
    second = apply_dedup([make_item("Different title", doi="10.1/a")], seen)[0]
    assert first.status == "NEW"
    assert second.status == "PREVIOUSLY_SEEN"


def test_url_dedup_marks_previously_seen() -> None:
    seen = {"items": {}, "index": {}}
    apply_dedup([make_item("A", url="https://example.test/a")], seen)
    second = apply_dedup([make_item("Different", url="https://example.test/a")], seen)[0]
    assert second.status == "PREVIOUSLY_SEEN"


def test_updated_item_detection() -> None:
    seen = {"items": {}, "index": {}}
    apply_dedup([make_item("Pavement Thermal", doi="10.1/a")], seen)
    updated = apply_dedup([make_item("Pavement Thermal", doi="10.1/a", abstract="New abstract")], seen)[0]
    assert updated.status == "UPDATED"
    assert "new_abstract_or_summary" in updated.update_reasons
