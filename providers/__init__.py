"""Unified market-data + AI-summary providers.

All external market-data access goes through `DataProvider` (Polygon.io,
"Massive API"). Catalyst summarization goes through `catalyst_summarizer`
(Anthropic Claude Haiku).
"""

from providers.data_provider import DataProvider, get_default_provider
from providers.catalyst_summarizer import summarize_catalyst, reset_summary_cache

__all__ = [
    "DataProvider",
    "get_default_provider",
    "summarize_catalyst",
    "reset_summary_cache",
]
