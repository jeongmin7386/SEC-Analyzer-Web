"""US stock provider backed by SEC EDGAR companyfacts."""

from __future__ import annotations

from typing import Any

from ..market_data import MarketDataError, get_stock_price_history
from ..metric_calculator import normalize_legacy_sec_rows
from ..sec_client import SECClient


COMMON_US_EXCHANGES = {
    "AAPL": "NASDAQ",
    "MSFT": "NASDAQ",
    "TSLA": "NASDAQ",
    "NVDA": "NASDAQ",
    "AMZN": "NASDAQ",
    "META": "NASDAQ",
    "GOOGL": "NASDAQ",
    "GOOG": "NASDAQ",
    "COST": "NASDAQ",
    "BRK.B": "NYSE",
    "JPM": "NYSE",
    "V": "NYSE",
    "UNH": "NYSE",
    "XOM": "NYSE",
}


class SECProvider:
    market = "US"

    def __init__(self, sec_client: SECClient) -> None:
        self.sec_client = sec_client

    def search_stocks(self, query: str) -> list[dict[str, Any]]:
        normalized = str(query or "").strip().upper()
        if not normalized:
            return []

        ticker_map = self.sec_client.get_ticker_map()
        lowered = normalized.lower()
        results: list[tuple[int, dict[str, Any]]] = []

        exact = ticker_map.get(normalized)
        if exact:
            results.append((0, self._resolved_stock(normalized, exact)))

        for ticker, profile in ticker_map.items():
            if exact and ticker == normalized:
                continue

            title = str(profile.get("title") or "")
            if ticker.lower() == lowered:
                rank = 0
            elif ticker.lower().startswith(lowered):
                rank = 1
            elif lowered in title.lower():
                rank = 2
            else:
                continue

            results.append((rank, self._resolved_stock(ticker, profile)))
            if len(results) >= 25:
                break

        unique: dict[str, tuple[int, dict[str, Any]]] = {}
        for rank, stock in results:
            current = unique.get(stock["symbol"])
            if current is None or rank < current[0]:
                unique[stock["symbol"]] = (rank, stock)

        return [
            stock
            for _, stock in sorted(
                unique.values(),
                key=lambda pair: (pair[0], pair[1]["symbol"]),
            )[:10]
        ]

    def get_company_profile(self, symbol: str) -> dict[str, Any]:
        profile = self.sec_client.get_company_profile(symbol.upper())
        return self._resolved_stock(profile["ticker"], profile)

    def get_financial_statements(self, symbol: str, years: int = 10) -> dict[str, Any]:
        sec_result = self.sec_client.fetch_annual_financials(symbol.upper(), limit=years)
        financials = normalize_legacy_sec_rows(sec_result["annual_rows"], currency="USD")
        cik = str(sec_result["profile"]["cik"]).zfill(10)

        for row in financials:
            row["sourceType"] = "SEC"
            row["sourceUrl"] = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            row.setdefault("metadata", {})
            row["metadata"].update(
                {
                    "selectedTags": sec_result.get("selected_tags", {}),
                    "reportingCurrency": "USD",
                    "formType": "10-K/20-F annual companyfacts",
                }
            )

        return {
            "company": {
                **self._resolved_stock(sec_result["profile"]["ticker"], sec_result["profile"]),
                "companyName": sec_result.get("entity_name") or sec_result["profile"].get("title"),
            },
            "financials": financials,
            "dataSource": "SEC",
            "currency": "USD",
            "cache": sec_result.get("cache", {}),
            "selectedTags": sec_result.get("selected_tags", {}),
        }

    def get_price_history(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str = "1y",
    ) -> list[dict[str, Any]]:
        del start_date, end_date
        try:
            return get_stock_price_history(symbol.upper(), period)
        except MarketDataError:
            raise

    def _resolved_stock(self, ticker: str, profile: dict[str, Any]) -> dict[str, Any]:
        symbol = ticker.upper()
        return {
            "market": "US",
            "symbol": symbol,
            "displaySymbol": symbol,
            "companyName": str(profile.get("title") or symbol),
            "exchange": COMMON_US_EXCHANGES.get(symbol, "US"),
            "currency": "USD",
            "cik": str(profile.get("cik") or "").zfill(10),
        }
