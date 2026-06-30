# STEPS Technical Intelligence Monitor

This repository contains a simple Python-based GitHub Actions monitor for HENGYUN Technology and STEPS.

It is an internal engineering intelligence workflow for monitoring topics such as:
- pavement cooling and urban heat mitigation
- thermal energy pavement and heat harvesting
- RTSU and related system-engineering relevance
- measurement, validation, and test methods
- alternative and competing solutions
- patent and novelty watch

## Purpose

This monitor does not make performance claims or imply verified outcomes. It collects publicly available signals for internal technical review only.

## Setup

```bash
python3 -m pip install -r requirements.txt
python3 src/main.py
python3 src/weekly_report.py
```

## Configuration

The workflow uses config.yaml for:
- source URLs
- monitoring keywords
- category definitions

## Limitations

- No paid APIs are required.
- If a source blocks scraping or returns 403/404, the issue is recorded under source health / fetch issues.
- Findings should be treated as internal engineering intelligence requiring human review.

## GitHub Actions

The workflow in .github/workflows/daily.yml runs the monitor daily and writes generated reports into the reports directory.
