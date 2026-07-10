"""Stock search service wrapper."""

from __future__ import annotations

from typing import Any

from .market_resolver import MarketResolver


class StockSearchService:
    def __init__(self, resolver: MarketResolver) -> None:
        self.resolver = resolver

    def search(self, query: str, market: str = "AUTO") -> dict[str, Any]:
        return self.resolver.search(query, market)
