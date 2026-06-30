from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

LAST_CLASSIFIED_ITEMS: List[Dict[str, Any]] = []
LAST_FILTERED_ITEMS: List[Dict[str, Any]] = []
SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "reports" / "classification_state.json"


def classify_items(
    items: List[Dict[str, Any]],
    keywords: List[str],
    categories: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    global LAST_CLASSIFIED_ITEMS, LAST_FILTERED_ITEMS

    rules = load_filtering_rules()
    classified_items: List[Dict[str, Any]] = []
    filtered_items: List[Dict[str, Any]] = []

    for item in items:
        title_text = normalize_text(item.get("title", ""))
        summary_text = normalize_text(item.get("summary", ""))
        full_text = f"{title_text} {summary_text}".lower()
        matched_keywords = [keyword for keyword in keywords if keyword.lower() in full_text]

        matched_categories = []
        if categories:
            for category in categories:
                category_keywords = category.get("keywords", [])
                if any(keyword.lower() in full_text for keyword in category_keywords):
                    matched_categories.append(category.get("name", "General"))

        filtered_reason = should_filter_out(full_text, rules)
        if filtered_reason:
            filtered_items.append({
                "title": title_text,
                "source_name": item.get("source_name", "Unknown"),
                "filter_reason": filtered_reason,
            })
            continue

        source_type = item.get("source_type", "unknown")
        source_category = source_type if source_type != "unknown" else "unknown"
        source_quality = assess_source_quality(source_type, item.get("source_name", ""))
        technical_category = matched_categories[0] if matched_categories else "General technical intelligence"
        relevance_to_steps = assess_relevance(full_text, matched_keywords, rules)
        technical_risk_or_opportunity = assess_risk_or_opportunity(full_text)
        validation_implication = assess_validation(full_text)
        competitor_or_alternative_implication = assess_competitor(full_text)
        patent_or_novelty_implication = assess_patent_novelty(full_text)
        recommended_action = assess_action(full_text, relevance_to_steps)

        classified_items.append({
            **item,
            "title": title_text,
            "source_category": source_category,
            "source_quality": source_quality,
            "technical_category": technical_category,
            "matched_keywords": matched_keywords,
            "relevance_to_steps": relevance_to_steps,
            "technical_risk_or_opportunity": technical_risk_or_opportunity,
            "validation_implication": validation_implication,
            "competitor_or_alternative_implication": competitor_or_alternative_implication,
            "patent_or_novelty_implication": patent_or_novelty_implication,
            "recommended_action": recommended_action,
        })

    LAST_CLASSIFIED_ITEMS = classified_items
    LAST_FILTERED_ITEMS = filtered_items
    write_classification_snapshot(classified_items, filtered_items)
    return classified_items


def get_last_classified_items() -> List[Dict[str, Any]]:
    if LAST_CLASSIFIED_ITEMS:
        return LAST_CLASSIFIED_ITEMS
    return read_classification_snapshot().get("classified_items", [])


def get_filtered_false_positives() -> List[Dict[str, Any]]:
    if LAST_FILTERED_ITEMS:
        return LAST_FILTERED_ITEMS
    return read_classification_snapshot().get("filtered_items", [])


def write_classification_snapshot(classified_items: List[Dict[str, Any]], filtered_items: List[Dict[str, Any]]) -> None:
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "classified_items": classified_items,
        "filtered_items": filtered_items,
    }
    SNAPSHOT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_classification_snapshot() -> Dict[str, Any]:
    if not SNAPSHOT_PATH.exists():
        return {"classified_items": [], "filtered_items": []}
    try:
        return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"classified_items": [], "filtered_items": []}


def load_filtering_rules() -> Dict[str, Any]:
    config_path = Path(__file__).resolve().parent.parent / "config.yaml"
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    return config.get("filtering", {})


def normalize_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    if isinstance(value, dict):
        return " ".join(str(item) for item in value.values() if item)
    return str(value)


def should_filter_out(text: str, rules: Dict[str, Any]) -> Optional[str]:
    false_positive_terms = [term.lower() for term in rules.get("false_positive_terms", [])]
    if any(term in text for term in false_positive_terms):
        return "unrelated false positive"

    pavement_terms = [term.lower() for term in rules.get("pavement_urban_terms", [])]
    thermal_terms = [term.lower() for term in rules.get("thermal_terms", [])]
    has_pavement_term = any(term in text for term in pavement_terms)
    has_thermal_term = any(term in text for term in thermal_terms)

    if not has_pavement_term:
        return "missing pavement or urban term"
    if not has_thermal_term:
        return "missing thermal term"

    return None


def assess_source_quality(source_type: str, source_name: str) -> str:
    source_name_lower = source_name.lower()
    if source_type == "academic":
        return "high"
    if source_type == "patent":
        return "medium-high"
    if source_type == "news" or "google news" in source_name_lower:
        return "secondary / needs verification"
    return "unknown"


def assess_relevance(title: str, matched_keywords: List[str], rules: Dict[str, Any]) -> str:
    if not title:
        return "low"

    pavement_terms = [term.lower() for term in rules.get("pavement_urban_terms", [])]
    thermal_terms = [term.lower() for term in rules.get("thermal_terms", [])]
    technical_terms = [term.lower() for term in rules.get("technical_implication_terms", [])]
    medium_terms = [term.lower() for term in rules.get("medium_relevance_terms", [])]
    low_terms = [term.lower() for term in rules.get("low_relevance_terms", [])]

    has_pavement_term = any(term in title for term in pavement_terms)
    has_thermal_term = any(term in title for term in thermal_terms)
    has_technical_implication = any(term in title for term in technical_terms)

    if has_pavement_term and has_thermal_term and has_technical_implication:
        return "high"

    if any(term in title for term in medium_terms):
        return "medium"

    if any(term in title for term in low_terms):
        return "low"

    if has_pavement_term and has_thermal_term:
        return "general technical relevance"

    if matched_keywords:
        return "general technical relevance"

    return "low"


def assess_risk_or_opportunity(title: str) -> str:
    if any(token in title for token in ["measurement", "validation", "field", "monitoring", "test"]):
        return "Opportunity: validation and field-test relevance"
    if any(token in title for token in ["patent", "novelty", "new"]):
        return "Opportunity: patent and novelty watch"
    return "Monitor for engineering risk and implementation trade-offs"


def assess_validation(title: str) -> str:
    if any(token in title for token in ["measure", "measurement", "monitor", "validation", "field", "test"]):
        return "High: directly relevant to measurement and validation planning"
    return "Medium: requires human review for validation evidence"


def assess_competitor(title: str) -> str:
    if any(token in title for token in ["alternative", "competing", "reflective", "permeable", "phase", "evaporative"]):
        return "High: relevant to alternative or competing cooling concepts"
    return "Medium: monitor for comparison against alternative approaches"


def assess_patent_novelty(title: str) -> str:
    if any(token in title for token in ["patent", "novelty", "invention", "ip"]):
        return "High: patent or novelty signal detected"
    return "Low: no immediate novelty signal"


def assess_action(title: str, relevance: str) -> str:
    if relevance == "high":
        return "Review for engineering relevance, validation approach, and RTSU implications"
    if any(token in title for token in ["patent", "novelty"]):
        return "Track as a novelty watch item for internal review"
    if relevance == "medium":
        return "Keep as a medium-priority background item for technical review"
    return "Keep as low-priority background intelligence only"
