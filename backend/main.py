"""FastAPI entry point for the KR/US stock analysis web app."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.analyzer import AnalysisError, analyze_financials
from app.etf_analyzer import analyze_etf
from app.etf_holdings import ETFHoldingsError, get_etf_holdings, parse_manual_holdings
from app.market_data import (
    MarketDataError,
    get_exchange_rates,
    get_indices,
    get_stock_price_history,
    get_stock_splits,
)
from app.providers.opendart_provider import (
    OpenDARTConfigurationError,
    OpenDARTError,
    OpenDARTProvider,
)
from app.providers.sec_provider import SECProvider
from app.schemas import ETFAnalysisRequest, StockAnalysisRequest, UnifiedStockAnalysisRequest
from app.sec_client import DEFAULT_USER_AGENT, SECClient, SECClientError, SECConfigurationError
from app.services.market_resolver import MarketResolutionError, MarketResolver
from app.services.stock_analysis_service import StockAnalysisService
from app.services.stock_search_service import StockSearchService
from app.split_adjustment import apply_split_adjustments


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
SUPPORTED_PRICE_PERIODS = {"1d", "1w", "1m", "1y", "5y", "all"}


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="Global Stock Analyzer API",
    description="KR/US stock analysis API using SEC EDGAR and OpenDART",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sec_client = SECClient(user_agent=os.getenv("SEC_USER_AGENT", DEFAULT_USER_AGENT))
sec_provider = SECProvider(sec_client)
opendart_provider = OpenDARTProvider(api_key=os.getenv("OPENDART_API_KEY", ""))
market_resolver = MarketResolver(opendart_provider, sec_provider)
stock_search_service = StockSearchService(market_resolver)
stock_analysis_service = StockAnalysisService(market_resolver, opendart_provider, sec_provider)

DISPLAY_ORDER = (
    "eps_growth",
    "share_issuance_rate",
    "roe",
    "current_ratio",
    "debt_ratio",
    "net_income_growth",
    "net_profit_margin",
)

TICKER_ALIASES = {
    "APPL": "AAPL",
}


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "serviceName": "Global Stock Analyzer",
        "secUserAgentConfigured": bool(sec_client.user_agent.strip()),
        "openDartApiKeyConfigured": bool(opendart_provider.api_key),
        "companyfactsCacheDir": str(sec_client.companyfacts_cache.directory),
        "companyfactsCacheTtlSeconds": sec_client.companyfacts_cache.ttl_seconds,
    }


@app.get("/api/stocks/search")
def search_stocks(
    q: str = Query(..., min_length=1),
    market: str = Query(default="AUTO", pattern="^(AUTO|KR|US)$"),
) -> dict[str, Any]:
    try:
        return stock_search_service.search(q, market)
    except MarketResolutionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SECClientError as exc:
        raise HTTPException(status_code=502, detail=safe_error(str(exc))) from exc


@app.get("/api/stocks/{market}/{symbol}/profile")
def stock_profile(market: str, symbol: str) -> dict[str, Any]:
    try:
        return stock_analysis_service.get_profile(market, symbol)
    except MarketResolutionError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "candidates": exc.candidates}) from exc
    except (OpenDARTError, SECClientError) as exc:
        raise HTTPException(status_code=502, detail=safe_error(str(exc))) from exc


@app.get("/api/stocks/{market}/{symbol}/financials")
def stock_financials(
    market: str,
    symbol: str,
    years: int = Query(default=10, ge=1, le=20),
) -> dict[str, Any]:
    try:
        return stock_analysis_service.get_financials(market, symbol, years=years)
    except OpenDARTConfigurationError as exc:
        raise HTTPException(status_code=503, detail=safe_error(str(exc))) from exc
    except MarketResolutionError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "candidates": exc.candidates}) from exc
    except (OpenDARTError, SECClientError) as exc:
        raise HTTPException(status_code=502, detail=safe_error(str(exc))) from exc


@app.get("/api/stocks/{market}/{symbol}/prices")
def stock_prices(
    market: str,
    symbol: str,
    period: str = Query(default="1y", pattern="^(1d|1w|1m|1y|5y|all)$"),
) -> dict[str, Any]:
    try:
        return stock_analysis_service.get_prices(market, symbol, period=period)
    except MarketResolutionError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "candidates": exc.candidates}) from exc
    except (OpenDARTError, MarketDataError) as exc:
        raise HTTPException(status_code=502, detail=safe_error(str(exc))) from exc


@app.post("/api/stocks/analyze")
def analyze_unified_stock(payload: UnifiedStockAnalysisRequest) -> dict[str, Any]:
    try:
        return stock_analysis_service.analyze(
            market=payload.market,
            symbol=payload.symbol,
            preset_id=payload.presetId,
            years=payload.years,
            include_price=payload.includePrice,
            price_period=payload.pricePeriod,
        )
    except OpenDARTConfigurationError as exc:
        raise HTTPException(status_code=503, detail=safe_error(str(exc))) from exc
    except MarketResolutionError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": str(exc), "candidates": exc.candidates},
        ) from exc
    except (OpenDARTError, SECClientError, AnalysisError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=safe_error(str(exc))) from exc


@app.post("/api/analyze/stock")
def analyze_stock(payload: StockAnalysisRequest) -> dict[str, Any]:
    return build_stock_analysis(
        ticker=payload.ticker,
        include_price=payload.includePrice,
        price_period=payload.pricePeriod,
    )


@app.post("/api/analyze/etf")
def analyze_etf_endpoint(payload: ETFAnalysisRequest) -> dict[str, Any]:
    return build_etf_analysis(payload)


@app.get("/api/analysis/{ticker}")
def analyze_ticker(
    ticker: str,
    include_price: bool = True,
    price_period: str = Query(default="1y", pattern="^(1d|1w|1m|1y|5y|all)$"),
) -> dict[str, Any]:
    return build_stock_analysis(ticker, include_price, price_period)


@app.post("/api/etf-analysis")
def analyze_etf_ticker(payload: ETFAnalysisRequest) -> dict[str, Any]:
    return build_etf_analysis(payload)


@app.get("/api/markets/indices")
def indices(period: str = Query(default="1m", pattern="^(1d|1w|1m|1y|5y|all)$")) -> dict[str, Any]:
    return get_indices(period)


@app.get("/api/markets/stocks/{ticker}/history")
def stock_history(
    ticker: str,
    period: str = Query(default="1y", pattern="^(1d|1w|1m|1y|5y|all)$"),
) -> dict[str, Any]:
    symbol = resolve_ticker_alias(normalize_ticker(ticker))
    try:
        history = get_stock_price_history(symbol, period)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=safe_error(str(exc))) from exc
    return {"ticker": symbol, "period": period, "history": history}


@app.get("/api/exchange-rates")
def exchange_rates(period: str = Query(default="1m", pattern="^(1d|1w|1m|1y|5y|all)$")) -> dict[str, Any]:
    try:
        return get_exchange_rates(period)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=safe_error(str(exc))) from exc


def build_stock_analysis(
    ticker: str,
    include_price: bool = True,
    price_period: str = "1y",
) -> dict[str, Any]:
    requested_symbol = normalize_ticker(ticker)
    symbol = resolve_ticker_alias(requested_symbol)
    period = validate_price_period(price_period)
    warnings: list[str] = []
    if symbol != requested_symbol:
        warnings.append(f"{requested_symbol} ticker was normalized to {symbol}.")

    try:
        sec_result = sec_client.fetch_annual_financials(symbol, limit=10)
        financial_rows = sec_result["annual_rows"]
        split_adjustments: list[dict[str, Any]] = []
        try:
            splits = get_stock_splits(symbol)
            financial_rows, split_adjustments = apply_split_adjustments(financial_rows, splits)
        except MarketDataError as exc:
            warnings.append(str(exc))

        analysis = analyze_financials(financial_rows)
    except SECConfigurationError as exc:
        raise HTTPException(status_code=503, detail=safe_error(str(exc))) from exc
    except SECClientError as exc:
        raise HTTPException(status_code=502, detail=safe_error(str(exc))) from exc
    except AnalysisError as exc:
        raise HTTPException(status_code=422, detail=safe_error(str(exc))) from exc

    price_history: list[dict[str, Any]] = []
    if include_price:
        try:
            price_history = get_stock_price_history(symbol, period)
        except MarketDataError as exc:
            warnings.append(str(exc))

    return {
        "requestedTicker": requested_symbol,
        "ticker": symbol,
        "entityName": sec_result["entity_name"],
        "profile": sec_result["profile"],
        "selectedTags": sec_result["selected_tags"],
        "splitAdjustments": split_adjustments,
        "annualRows": analysis["annual_rows"],
        "metricRows": ordered_metric_rows(analysis["summaries"]),
        "averageScore": analysis["average_score"],
        "stabilityScore": analysis["stability_score"],
        "totalScore": analysis["total_score"],
        "maxScore": 7.0,
        "averageIsSuitable": analysis["average_is_suitable"],
        "stabilityIsSuitable": analysis["stability_is_suitable"],
        "isSuitable": analysis["is_suitable"],
        "averageVerdict": "적합" if analysis["average_is_suitable"] else "부적합",
        "stabilityVerdict": "적합" if analysis["stability_is_suitable"] else "부적합",
        "verdict": "적합" if analysis["is_suitable"] else "부적합",
        "priceHistory": price_history,
        "cache": sec_result.get("cache", {}),
        "warnings": warnings,
    }


def build_etf_analysis(payload: ETFAnalysisRequest) -> dict[str, Any]:
    requested_symbol = normalize_ticker(payload.ticker)
    manual_holdings = (payload.manualHoldings or "").strip()

    try:
        if manual_holdings:
            holdings = parse_manual_holdings(manual_holdings)
            holdings_source = "manual"
        else:
            holdings = get_etf_holdings(requested_symbol)
            holdings_source = "sample"
    except ETFHoldingsError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "manualInputRequired": True,
                "manualFormat": "AAPL:7.5, MSFT:7.2, NVDA:6.8",
            },
        ) from exc

    result = analyze_etf(requested_symbol, holdings, sec_client)
    result["holdings"] = holdings
    result["holdingsSource"] = holdings_source
    return result


def ordered_metric_rows(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key = {summary["key"]: summary for summary in summaries}
    return [by_key[key] for key in DISPLAY_ORDER if key in by_key]


def normalize_ticker(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="티커를 입력하세요.")
    if len(symbol) > 16 or not all(character.isalnum() or character in ".-" for character in symbol):
        raise HTTPException(status_code=400, detail="티커 형식이 올바르지 않습니다.")
    return symbol


def resolve_ticker_alias(symbol: str) -> str:
    return TICKER_ALIASES.get(symbol, symbol)


def validate_price_period(period: str) -> str:
    normalized = (period or "1y").strip().lower()
    if normalized not in SUPPORTED_PRICE_PERIODS:
        raise HTTPException(status_code=400, detail="지원하지 않는 가격 기간입니다.")
    return normalized


def safe_error(message: str) -> str:
    api_key = os.getenv("OPENDART_API_KEY", "")
    if api_key:
        message = message.replace(api_key, "[redacted]")
    return message


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found.")

        requested_path = FRONTEND_DIST / full_path
        if requested_path.is_file():
            return FileResponse(requested_path)
        return FileResponse(FRONTEND_DIST / "index.html")
