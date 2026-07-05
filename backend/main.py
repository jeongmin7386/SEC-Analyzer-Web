"""FastAPI entry point for the SEC EDGAR stock analysis web app."""

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
from app.schemas import ETFAnalysisRequest, StockAnalysisRequest
from app.sec_client import DEFAULT_USER_AGENT, SECClient, SECClientError, SECConfigurationError
from app.split_adjustment import apply_split_adjustments


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
SUPPORTED_PRICE_PERIODS = {"1d", "1w", "1m", "1y", "5y", "all"}


def cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI(
    title="SEC Stock Analyzer API",
    description="SEC EDGAR companyfacts based stock and ETF holdings analysis API",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

sec_client = SECClient(user_agent=os.getenv("SEC_USER_AGENT", DEFAULT_USER_AGENT))

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
        "secUserAgentConfigured": bool(sec_client.user_agent.strip()),
        "companyfactsCacheDir": str(sec_client.companyfacts_cache.directory),
        "companyfactsCacheTtlSeconds": sec_client.companyfacts_cache.ttl_seconds,
    }


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
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"ticker": symbol, "period": period, "history": history}


@app.get("/api/exchange-rates")
def exchange_rates(period: str = Query(default="1m", pattern="^(1d|1w|1m|1y|5y|all)$")) -> dict[str, Any]:
    try:
        return get_exchange_rates(period)
    except MarketDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


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
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SECClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

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
