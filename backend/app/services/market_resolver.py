"""Resolve a user stock query to a KR or US listing."""

from __future__ import annotations

import re
from typing import Any

from ..stock_master import normalize_kr_symbol
from ..providers.opendart_provider import OpenDARTProvider
from ..providers.sec_provider import SECProvider


MARKETS = {"AUTO", "KR", "US"}


class MarketResolutionError(ValueError):
    def __init__(self, message: str, candidates: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.candidates = candidates or []


class MarketResolver:
    def __init__(self, kr_provider: OpenDARTProvider, us_provider: SECProvider) -> None:
        self.kr_provider = kr_provider
        self.us_provider = us_provider

    def search(self, query: str, market: str = "AUTO") -> dict[str, Any]:
        normalized_market = normalize_market(market)
        normalized_query = str(query or "").strip()
        if not normalized_query:
            return {"query": query, "market": normalized_market, "results": [], "ambiguous": False}

        results = self._search_candidates(normalized_query, normalized_market)
        results = dedupe_results(results)
        return {
            "query": query,
            "market": normalized_market,
            "results": results,
            "ambiguous": len(results) > 1,
        }

    def resolve(self, query: str, market: str = "AUTO") -> dict[str, Any]:
        payload = self.search(query, market)
        results = payload["results"]
        if not results:
            raise MarketResolutionError(f"'{query}'에 해당하는 종목을 찾을 수 없습니다.")

        exact = exact_matches(query, results)
        if len(exact) == 1:
            return exact[0]
        if len(results) == 1:
            return results[0]

        raise MarketResolutionError(
            "시장 또는 종목 판별이 불확실합니다. 후보 목록에서 선택해 주세요.",
            candidates=results,
        )

    def _search_candidates(self, query: str, market: str) -> list[dict[str, Any]]:
        if market == "KR":
            return self.kr_provider.search_stocks(query)
        if market == "US":
            return self.us_provider.search_stocks(query)

        if is_kr_code_query(query):
            return self.kr_provider.search_stocks(query)
        if is_kr_suffix_query(query):
            return self.kr_provider.search_stocks(normalize_kr_symbol(query))

        results: list[dict[str, Any]] = []
        if is_us_ticker_candidate(query):
            results.extend(self.us_provider.search_stocks(query))
            results.extend(self.kr_provider.search_stocks(query))
        else:
            results.extend(self.kr_provider.search_stocks(query))
            results.extend(self.us_provider.search_stocks(query))
        return results


def normalize_market(value: str | None) -> str:
    market = str(value or "AUTO").strip().upper()
    if market not in MARKETS:
        raise MarketResolutionError("market은 AUTO, KR, US 중 하나여야 합니다.")
    return market


def is_kr_code_query(query: str) -> bool:
    return bool(re.fullmatch(r"\d{6}", str(query or "").strip()))


def is_kr_suffix_query(query: str) -> bool:
    return bool(re.fullmatch(r"\d{6}\.(KS|KQ)", str(query or "").strip().upper()))


def is_us_ticker_candidate(query: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]{0,9}", str(query or "").strip()))


def exact_matches(query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = str(query or "").strip().upper()
    kr_normalized = normalize_kr_symbol(normalized)
    exact: list[dict[str, Any]] = []
    for result in results:
        symbol = str(result.get("symbol") or "").upper()
        display = str(result.get("displaySymbol") or "").upper()
        name = str(result.get("companyName") or "").upper()
        if normalized in {symbol, display, name} or kr_normalized == symbol:
            exact.append(result)
    return exact


def dedupe_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for result in results:
        key = (str(result.get("market")), str(result.get("symbol")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped
