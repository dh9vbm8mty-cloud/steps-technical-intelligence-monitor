from fetchers.crossref import fetch_crossref
from fetchers.generic_feed import fetch_generic_feed
from fetchers.generic_html import fetch_generic_html
from fetchers.openalex import fetch_openalex
from fetchers.patents import fetch_patents_fallback
from fetchers.project_sources import fetch_project_source
from fetchers.semantic_scholar import fetch_semantic_scholar

__all__ = [
    "fetch_crossref",
    "fetch_generic_feed",
    "fetch_generic_html",
    "fetch_openalex",
    "fetch_patents_fallback",
    "fetch_project_source",
    "fetch_semantic_scholar",
]
