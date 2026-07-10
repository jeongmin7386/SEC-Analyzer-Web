"""Unified KR/US stock analysis service."""

from __future__ import annotations

from datetime import date
from typing import Any

from ..market_data import MarketDataError
from ..metric_calculator import analyze_normalized_financials
from ..providers.opendart_provider import OpenDARTProvider
from ..providers.sec_provider import SECProvider
from .market_resolver import MarketResolutionError, MarketResolver, normalize_market


NORMALIZED_FIELDS = (
    "revenue",
    "operatingIncome",
    "netIncome",
    "totalAssets",
    "totalLiabilities",
    "totalEquity",
    "currentAssets",
    "currentLiabilities",
    "sharesOutstanding",
    "eps",
    "operatingCashFlow",
)


class StockAnalysisService:
    def __init__(
        self,
        resolver: MarketResolver,
        kr_provider: OpenDARTProvider,
        us_provider: SECProvider,
    ) -> None:
        self.resolver = resolver
        self.providers = {
            "KR": kr_provider,
            "US": us_provider,
        }

    def analyze(
        self,
        *,
        market: str,
        symbol: str,
        preset_id: str = "default",
        years: int = 10,
        include_price: bool = True,
        price_period: str = "1y",
    ) -> dict[str, Any]:
        resolved = self.resolve_symbol(symbol, market)
        provider = self.providers[resolved["market"]]
        warnings: list[str] = []

        provider_payload = provider.get_financial_statements(resolved["symbol"], years=years)
        financials = provider_payload["financials"]
        company = {**resolved, **provider_payload.get("company", {})}
        analysis = analyze_normalized_financials(
            financials,
            preset_id=preset_id,
            industry=company.get("industry"),
        )

        price_history: list[dict[str, Any]] = []
        if include_price:
            try:
                price_history = provider.get_price_history(
                    resolved["symbol"],
                    period=price_period,
                )
            except (MarketDataError, RuntimeError) as exc:
                warnings.append(str(exc))

        warnings.extend(provider_payload.get("warnings") or [])
        missing_fields = missing_normalized_fields(financials)
        as_of_date = latest_as_of_date(financials)
        score = analysis["score"]

        return {
            "company": company,
            "market": resolved["market"],
            "currency": provider_payload.get("currency") or company.get("currency"),
            "dataSource": provider_payload.get("dataSource"),
            "asOfDate": as_of_date,
            "financials": financials,
            "metrics": analysis["metric_rows"],
            "score": score,
            "warnings": warnings,
            "missingFields": missing_fields,
            "priceHistory": price_history,
            "cache": provider_payload.get("cache", {}),
            "selectedTags": provider_payload.get("selectedTags", {}),
            "ticker": company.get("displaySymbol") or company.get("symbol"),
            "entityName": company.get("companyName"),
            "profile": company,
            "annualRows": analysis["annual_rows"],
            "metricRows": analysis["metric_rows"],
            "averageScore": score["averageScore"],
            "stabilityScore": score["stabilityScore"],
            "totalScore": score["totalScore"],
            "maxScore": score["maxScore"],
            "averageIsSuitable": score["averageScore"] >= 3.0,
            "stabilityIsSuitable": score["stabilityScore"] >= 3.0,
            "isSuitable": score["isSuitable"],
            "averageVerdict": "적합" if score["averageScore"] >= 3.0 else "부적합",
            "stabilityVerdict": score["verdict"],
            "verdict": score["verdict"],
            "dataNotice": data_notice(resolved["market"], as_of_date),
        }

    def resolve_symbol(self, symbol: str, market: str) -> dict[str, Any]:
        normalized_market = normalize_market(market)
        if normalized_market == "AUTO":
            return self.resolver.resolve(symbol, "AUTO")

        provider = self.providers[normalized_market]
        matches = provider.search_stocks(symbol)
        exact = [
            match
            for match in matches
            if str(match.get("symbol")).upper() == str(symbol).upper()
            or str(match.get("displaySymbol")).upper() == str(symbol).upper()
        ]
        if exact:
            return exact[0]
        if len(matches) == 1:
            return matches[0]
        if matches:
            raise MarketResolutionError("후보 목록에서 분석할 종목을 선택해 주세요.", matches)
        raise MarketResolutionError(f"{normalized_market} 시장에서 '{symbol}' 종목을 찾을 수 없습니다.")

    def get_profile(self, market: str, symbol: str) -> dict[str, Any]:
        resolved_market = normalize_market(market)
        if resolved_market == "AUTO":
            resolved = self.resolver.resolve(symbol, "AUTO")
            return resolved
        return self.providers[resolved_market].get_company_profile(symbol)

    def get_financials(self, market: str, symbol: str, years: int = 10) -> dict[str, Any]:
        resolved_market = normalize_market(market)
        if resolved_market == "AUTO":
            resolved = self.resolver.resolve(symbol, "AUTO")
            resolved_market = resolved["market"]
            symbol = resolved["symbol"]
        return self.providers[resolved_market].get_financial_statements(symbol, years=years)

    def get_prices(self, market: str, symbol: str, period: str = "1y") -> dict[str, Any]:
        resolved_market = normalize_market(market)
        if resolved_market == "AUTO":
            resolved = self.resolver.resolve(symbol, "AUTO")
            resolved_market = resolved["market"]
            symbol = resolved["symbol"]
        history = self.providers[resolved_market].get_price_history(symbol, period=period)
        return {"market": resolved_market, "symbol": symbol, "period": period, "history": history}


def missing_normalized_fields(financials: list[dict[str, Any]]) -> list[str]:
    missing: list[str] = []
    for field in NORMALIZED_FIELDS:
        if all(row.get(field) in (None, "") for row in financials):
            missing.append(field)
    return missing


def latest_as_of_date(financials: list[dict[str, Any]]) -> str:
    dates = [str(row.get("filedAt")) for row in financials if row.get("filedAt")]
    if dates:
        return sorted(dates)[-1]
    years = [int(row["fiscalYear"]) for row in financials if row.get("fiscalYear")]
    if years:
        return str(max(years))
    return date.today().isoformat()


def data_notice(market: str, as_of_date: str) -> str:
    if market == "KR":
        return f"최근 거래일 및 OpenDART 공시 기준 데이터입니다. 기준일: {as_of_date}"
    return f"SEC EDGAR companyfacts 및 최근 거래일 기준 데이터입니다. 기준일: {as_of_date}"
