# STEPS Technical Intelligence Monitor

Internal engineering intelligence monitor for the broad technical landscape surrounding STEPS.

This repository is distinct from the Hydronic Pavement Monitor. Hydronic Phase 1 patterns are used here only for engineering structure: normalized records, source-specific fetchers, persistent history, de-duplication, source health, retry/backoff, saved run records, weekly aggregation, and tests. The STEPS taxonomy is broader and does not reject passive pavement cooling alternatives merely because they are non-hydronic.

## Purpose

The monitor tracks source signals relevant to pavement thermal management, urban heat mitigation, active and passive cooling alternatives, heat harvesting, embedded thermal systems, field validation, construction, durability, maintenance, hydraulic and thermal performance, controls, sensors, energy consumption, commercial systems, demonstration projects, and patent review triggers.

AI-generated classification is triage support only. It must not be treated as engineering performance evidence, validation evidence, regulatory conclusion, patentability conclusion, infringement conclusion, commercial maturity conclusion, environmental claim, or public-facing STEPS claim.

## Source Families

Search families are configured in `config/taxonomy.yaml`:

- pavement thermal management
- urban heat mitigation
- active pavement cooling
- passive cooling alternatives
- heat harvesting and embedded thermal systems
- field validation and measurement
- construction, durability, and maintenance
- controls, sensors, and monitoring
- energy and parasitic load
- commercial and field deployment

Source groups are configured in `config/sources.yaml`:

- academic: Crossref, OpenAlex, Semantic Scholar
- project / commercial architecture: configurable generic project sources
- patents: Google Patents fallback only

The Google Patents fallback is not a complete patent intelligence subsystem. Patent hits are review triggers only.

## Taxonomy

Items are normalized into structured records with item type, technology-family tags, STEPS relevance, project maturity, validation quality, engineering relevance tags, competitor / alternative relevance, patent review trigger, source confidence, and human review queue status.

Relevance levels are `Critical`, `High`, `Medium`, `Background`, and `Reject`. Critical classification requires stronger evidence than keyword count, such as field or operational evidence, validation relevance, durability or construction impact, system-level engineering implication, or patent review trigger.

## Registry

Persistent state is stored under `data/`:

- `data/registry/items.jsonl`: retained `NEW` and `UPDATED` records
- `data/registry/seen_items.json`: de-duplication registry
- `data/registry/source_health.json`: persistent source health
- `data/runs/*.json`: saved run snapshots

De-duplication uses DOI, patent publication number, canonical URL, normalized title, title plus organization plus year, and project title plus organization plus location.

## Reports

Daily reports:

- `reports/daily/YYYY-MM-DD-steps-technical-brief.md`
- `reports/daily/YYYY-MM-DD-steps-technical-brief-notebooklm.txt`

Weekly reports:

- `reports/weekly/YYYY-MM-DD-weekly-steps-technical-brief.md`
- `reports/weekly/weekly-steps-technical-brief-notebooklm.txt`

Weekly reports aggregate the previous seven days of saved run history. They do not refetch sources.

## Source Health

Fetchers use bounded retry/backoff for HTTP 429, 502, 503, and 504, including `Retry-After` where provided.

Source health records include last attempt, last success, last status, last HTTP code, consecutive failures, item count, and last error.

If important sources fail, reports state that monitoring coverage is degraded and absence of findings is inconclusive for affected source domains.

## Human Review

The default human review queue includes all Critical items, all High items, and Medium items with explicit engineering review triggers. Background items remain in the registry but normally do not enter the human review queue.

## Local Commands

Install dependencies:

```bash
pip install -r requirements.txt
```

Run tests:

```bash
pytest -q
```

Run one monitor cycle:

```bash
python src/main.py --mode monitor
```

Run a wider backfill cycle:

```bash
python src/main.py --mode backfill
```

Generate weekly reports from saved history only:

```bash
python src/report_weekly.py
```

Do not push generated changes automatically. Review generated data and reports before committing.
