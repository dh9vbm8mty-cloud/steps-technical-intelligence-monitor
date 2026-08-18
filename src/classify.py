from __future__ import annotations

from typing import Any, Dict, List

from models import IntelligenceItem


def classify_items(items: List[IntelligenceItem], taxonomy: Dict[str, Any]) -> List[IntelligenceItem]:
    rules = taxonomy.get("classification", {})
    for item in items:
        classify_item(item, rules)
    return items


def classify_item(item: IntelligenceItem, rules: Dict[str, Any]) -> IntelligenceItem:
    text = item_text(item)
    if is_unrelated_false_positive(text, rules):
        reject(item)
        return item

    has_domain = has_any(text, rules.get("domain_terms", []))
    has_thermal = has_any(text, rules.get("thermal_terms", []))
    families = detect_technology_families(text, rules)
    item.technology_families = families
    item.engineering_relevance_tags = detect_engineering_tags(text)
    item.project_maturity = detect_project_maturity(item, text)
    item.validation_quality = detect_validation_quality(text)
    item.patent_review_trigger = item.item_type == "Patent" or has_any(text, ["patent", "invention", "intellectual property", "prior art"])
    item.alternative_or_competitor_relevance = detect_alternative_competitor_relevance(families, text)
    item.source_confidence = source_confidence(item.source_name, item.item_type)

    if not has_domain and not has_thermal and not families:
        reject(item)
        return item

    item.relevance = determine_relevance(item, text, has_domain, has_thermal, rules)
    item.human_review_required = should_enter_human_review_queue(item, text, rules)
    return item


def item_text(item: IntelligenceItem) -> str:
    parts = [
        item.title,
        item.abstract_or_summary or "",
        item.publication or "",
        item.organization or "",
        item.item_type or "",
    ]
    return " ".join(part for part in parts if part).lower()


def reject(item: IntelligenceItem) -> None:
    item.relevance = "Reject"
    item.status = "REJECTED"
    item.human_review_required = False
    item.technology_families = []
    item.engineering_relevance_tags = []


def is_unrelated_false_positive(text: str, rules: Dict[str, Any]) -> bool:
    if not has_any(text, rules.get("unrelated_false_positive_terms", [])):
        return False
    return not has_any(text, rules.get("domain_terms", []))


def determine_relevance(
    item: IntelligenceItem,
    text: str,
    has_domain: bool,
    has_thermal: bool,
    rules: Dict[str, Any],
) -> str:
    strong_signal = has_strong_critical_signal(item, text)
    direct_engineering = has_domain and (has_thermal or bool(item.technology_families))
    if strong_signal and direct_engineering:
        return "Critical"
    if direct_engineering and has_any(text, rules.get("explicit_review_triggers", [])):
        return "High"
    if item.patent_review_trigger and direct_engineering:
        return "High"
    if direct_engineering:
        return "Medium"
    if item.technology_families:
        return "Background"
    return "Reject"


def has_strong_critical_signal(item: IntelligenceItem, text: str) -> bool:
    if item.patent_review_trigger:
        return True
    if has_any(text, ["full-scale", "full scale", "operational", "commercial deployment", "multi-season", "multi-year"]):
        return True
    if has_any(text, ["field demonstration", "field test", "field experiment", "pilot", "demonstration project"]):
        return True
    if has_any(text, ["durability failure", "failure mode", "thermal cracking", "pumping energy", "parasitic energy"]):
        return True
    if has_any(text, ["validation method", "independent validation", "heat flux measurement"]):
        return True
    return False


def should_enter_human_review_queue(item: IntelligenceItem, text: str, rules: Dict[str, Any]) -> bool:
    if item.relevance in {"Critical", "High"}:
        return True
    if item.relevance == "Medium":
        return has_any(text, rules.get("explicit_review_triggers", [])) or item.patent_review_trigger
    return False


def detect_technology_families(text: str, rules: Dict[str, Any]) -> List[str]:
    families = []
    for family, terms in rules.get("technology_families", {}).items():
        if has_any(text, terms):
            families.append(family)
    if not families and has_any(text, ["pavement", "asphalt", "road surface"]) and has_any(text, ["thermal", "temperature", "cooling", "heat"]):
        families.append("Other")
    return families


def detect_engineering_tags(text: str) -> List[str]:
    tags_by_term = {
        "thermal performance": ["thermal performance", "heat transfer", "cooling performance"],
        "hydraulic performance": ["hydraulic", "flow rate", "pressure drop"],
        "surface temperature": ["surface temperature"],
        "subsurface temperature": ["subsurface temperature"],
        "heat flux": ["heat flux"],
        "pumping / energy consumption": ["pumping energy", "energy consumption", "power consumption", "parasitic energy"],
        "control strategy": ["control strategy", "control system", "thermal control"],
        "sensor / instrumentation": ["sensor", "instrumentation", "monitoring", "iot"],
        "construction": ["construction", "constructability", "installation"],
        "durability": ["durability", "fatigue", "cracking"],
        "maintenance": ["maintenance"],
        "environmental / climatic conditions": ["climate", "microclimate", "weather", "outdoor"],
        "field validation": ["field", "pilot", "demonstration", "validation"],
        "commercial maturity": ["commercial", "product", "deployment"],
        "urban heat mitigation": ["urban heat", "heat island", "microclimate"],
        "system integration": ["system integration", "heat pump", "thermal storage", "district heating", "district cooling"],
        "useful heat recovery": ["heat recovery", "heat harvesting", "thermal energy harvesting"],
        "alternative technology": ["reflective", "permeable", "evaporative", "phase change", "thermochromic"],
        "competitor relevance": ["competing", "alternative", "commercial product"],
        "patent review trigger": ["patent", "invention", "prior art"],
    }
    return [tag for tag, terms in tags_by_term.items() if has_any(text, terms)]


def detect_project_maturity(item: IntelligenceItem, text: str) -> str:
    if item.item_type in {"Commercial Deployment", "Company / Product"} or has_any(text, ["commercial product", "commercial deployment"]):
        return "Commercial Product / Deployment"
    if has_any(text, ["operational infrastructure", "operational", "in operation"]):
        return "Operational Infrastructure"
    if has_any(text, ["demonstration project", "demonstration"]):
        return "Demonstration"
    if "pilot" in text:
        return "Pilot"
    if has_any(text, ["outdoor experimental", "test section", "field experiment", "field test"]):
        return "Outdoor Experimental Section"
    if has_any(text, ["laboratory", "lab scale", "prototype"]):
        return "Laboratory Prototype"
    if has_any(text, ["numerical", "simulation", "model"]):
        return "Numerical Model"
    if "concept" in text:
        return "Concept"
    return "Unknown"


def detect_validation_quality(text: str) -> str:
    if "independent validation" in text:
        return "Independent Validation"
    if has_any(text, ["multi-year", "multiyear"]):
        return "Multi-Year Operation"
    if has_any(text, ["multi-season", "multiseason"]):
        return "Multi-Season Monitoring"
    if has_any(text, ["full-scale field", "full scale field"]):
        return "Full-Scale Field Demonstration"
    if "field experiment" in text:
        return "Controlled Field Experiment"
    if has_any(text, ["outdoor test", "short-term outdoor", "field test"]):
        return "Short-Term Outdoor Test"
    if has_any(text, ["laboratory measurement", "lab measurement"]):
        return "Laboratory Measurement"
    if has_any(text, ["simulation", "numerical model"]):
        return "Simulation Only"
    return "Unknown"


def detect_alternative_competitor_relevance(families: List[str], text: str) -> str:
    alternative_families = {
        "Passive Reflective",
        "Permeable / Evaporative",
        "Water-Retaining",
        "Green / Nature-Based Pavement",
        "Phase Change Material",
        "Thermochromic / Responsive Material",
        "Thermoelectric",
    }
    if alternative_families.intersection(families) or has_any(text, ["alternative", "competing", "competitor"]):
        return "Reported"
    return "Not Reported"


def source_confidence(source_name: str, item_type: str) -> str:
    lower = source_name.lower()
    if lower in {"crossref", "openalex", "semantic scholar"}:
        return "High for bibliographic discovery; engineering claims require human review"
    if item_type == "Patent":
        return "Limited patent discovery signal; human patent review required"
    return "Needs verification"


def has_any(text: str, terms: List[str]) -> bool:
    return any(term.lower() in text for term in terms)
