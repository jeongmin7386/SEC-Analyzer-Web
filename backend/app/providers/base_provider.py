"""Base provider protocol for market-specific stock data."""

from __future__ import annotations

from typing import Any, Protocol


class StockDataProvider(Protocol):
    market: str

    def search_stocks(self, query: str) -> list[dict[str, Any]]:
        ...

    def get_company_profile(self, symbol: str) -> dict[str, Any]:
        ...

    def get_financial_statements(self, symbol: str, years: int = 10) -> dict[str, Any]:
        ...

    def get_price_history(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str = "1y",
    ) -> list[dict[str, Any]]:
        ...

