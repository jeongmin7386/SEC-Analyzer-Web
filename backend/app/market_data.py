"""Market, stock price, and exchange-rate data helpers."""

from __future__ import annotations

from datetime import date, timedelta
import os
from pathlib import Path
import tempfile
import time
from typing import Any

import requests

try:
    import yfinance as yf
except ImportError:
    yf = None


YFINANCE_CACHE_DIR = Path(__file__).resolve().parents[1] / "cache" / "yfinance"
if yf is not None:
    try:
        YFINANCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        YFINANCE_CACHE_DIR = Path(tempfile.gettempdir()) / "sec-stock-analyzer-yfinance"
        YFINANCE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if hasattr(yf, "set_tz_cache_location"):
        yf.set_tz_cache_location(str(YFINANCE_CACHE_DIR))


class MarketDataError(RuntimeError):
    """Raised when market data cannot be fetched."""


PERIODS: dict[str, dict[str, str]] = {
    "1d": {"yf_period": "1d", "interval": "5m"},
    "1w": {"yf_period": "5d", "interval": "30m"},
    "1m": {"yf_period": "1mo", "interval": "1d"},
    "1y": {"yf_period": "1y", "interval": "1d"},
    "5y": {"yf_period": "5y", "interval": "1wk"},
    "all": {"yf_period": "max", "interval": "1mo"},
}

EXCHANGE_PERIOD_DAYS = {
    "1d": 1,
    "1w": 7,
    "1m": 30,
    "1y": 365,
    "5y": 365 * 5,
    "all": 365 * 10,
}

INDEX_SYMBOLS = (
    {"key": "nasdaq", "name": "Nasdaq", "symbol": "^IXIC"},
    {"key": "sp500", "name": "S&P 500", "symbol": "^GSPC"},
    {"key": "dow", "name": "Dow", "symbol": "^DJI"},
    {"key": "kospi", "name": "KOSPI", "symbol": "^KS11"},
    {"key": "kosdaq", "name": "KOSDAQ", "symbol": "^KQ11"},
    {"key": "kospi200", "name": "KOSPI 200", "symbol": "^KS200"},
)

EXCHANGE_PAIRS = (
    {"key": "USD_KRW", "name": "USD/KRW", "base": "USD"},
    {"key": "JPY_KRW", "name": "JPY/KRW", "base": "JPY"},
    {"key": "EUR_KRW", "name": "EUR/KRW", "base": "EUR"},
)


def get_indices(period: str = "1m") -> dict[str, Any]:
    payload_period = normalize_period(period)
    items = []

    for item in INDEX_SYMBOLS:
        try:
            history = get_symbol_history(item["symbol"], payload_period)
            items.append(
                {
                    **item,
                    "current": latest_close(history),
                    "change": close_change(history),
                    "changePercent": close_change_percent(history),
                    "history": history,
                    "error": None,
                }
            )
        except MarketDataError as exc:
            items.append(
                {
                    **item,
                    "current": None,
                    "change": None,
                    "changePercent": None,
                    "history": [],
                    "error": str(exc),
                }
            )

    return {"period": payload_period, "items": items}


def get_stock_price_history(ticker: str, period: str = "1y") -> list[dict[str, Any]]:
    symbol = ticker.strip().upper()
    if not symbol:
        raise MarketDataError("Ticker is required.")
    return get_symbol_history(symbol, normalize_period(period))


def get_stock_splits(ticker: str) -> list[dict[str, Any]]:
    if yf is None:
        raise MarketDataError("yfinance is not installed.")

    symbol = ticker.strip().upper()
    if not symbol:
        raise MarketDataError("Ticker is required.")

    try:
        splits = yf.Ticker(symbol).splits
    except Exception as exc:
        raise MarketDataError(f"Could not load stock split data for {symbol}: {exc}") from exc

    if splits is None or splits.empty:
        return []

    rows: list[dict[str, Any]] = []
    for index, value in splits.items():
        label = index.isoformat() if hasattr(index, "isoformat") else str(index)
        rows.append({"date": label, "ratio": float(value)})
    return rows


def get_symbol_history(symbol: str, period: str = "1m") -> list[dict[str, Any]]:
    if yf is None:
        raise MarketDataError("yfinance is not installed.")

    period_config = PERIODS[normalize_period(period)]
    frame = None
    last_error: Exception | None = None

    for attempt in range(3):
        try:
            frame = yf.Ticker(symbol).history(
                period=period_config["yf_period"],
                interval=period_config["interval"],
                auto_adjust=False,
            )
            if frame is not None and not frame.empty and "Close" in frame:
                break
        except Exception as exc:
            last_error = exc

        if attempt < 2:
            time.sleep(0.6 * (attempt + 1))

    if frame is None or frame.empty or "Close" not in frame:
        try:
            frame = yf.download(
                symbol,
                period=period_config["yf_period"],
                interval=period_config["interval"],
                auto_adjust=False,
                progress=False,
                threads=False,
            )
        except Exception as exc:
            last_error = exc

    if frame is None or frame.empty or "Close" not in frame:
        suffix = f" ({last_error})" if last_error else ""
        raise MarketDataError(f"{symbol} price data is temporarily unavailable{suffix}.")

    close = frame["Close"].dropna()
    if close.empty:
        raise MarketDataError(f"{symbol} close data is empty.")

    points: list[dict[str, Any]] = []
    for index, value in close.items():
        label = index.isoformat() if hasattr(index, "isoformat") else str(index)
        points.append({"date": label, "close": float(value)})

    return points


def latest_close(history: list[dict[str, Any]]) -> float | None:
    if not history:
        return None
    return history[-1]["close"]


def close_change(history: list[dict[str, Any]]) -> float | None:
    if len(history) < 2:
        return None
    return history[-1]["close"] - history[-2]["close"]


def close_change_percent(history: list[dict[str, Any]]) -> float | None:
    if len(history) < 2 or history[-2]["close"] == 0:
        return None
    return (history[-1]["close"] - history[-2]["close"]) / abs(history[-2]["close"])


def get_exchange_rates(period: str = "1m") -> dict[str, Any]:
    payload_period = normalize_period(period)
    start, end = exchange_date_range(payload_period)
    rates_by_date = fetch_frankfurter_rates(start, end)

    series = convert_usd_rates_to_pairs(rates_by_date)
    items = []
    for pair in EXCHANGE_PAIRS:
        history = series[pair["key"]]
        items.append(
            {
                **pair,
                "current": latest_rate(history),
                "change": rate_change(history),
                "changePercent": rate_change_percent(history),
                "history": history,
            }
        )

    return {"period": payload_period, "items": items}


def fetch_frankfurter_rates(start: date, end: date) -> dict[str, dict[str, float]]:
    base_url = os.getenv("EXCHANGE_RATE_BASE_URL", "https://api.frankfurter.app").rstrip("/")

    if start >= end:
        url = f"{base_url}/latest"
        params = {"from": "USD", "to": "KRW,JPY,EUR"}
    else:
        url = f"{base_url}/{start.isoformat()}..{end.isoformat()}"
        params = {"from": "USD", "to": "KRW,JPY,EUR"}

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise MarketDataError(f"Could not load exchange-rate data: {exc}") from exc
    except ValueError as exc:
        raise MarketDataError("Exchange-rate API did not return valid JSON.") from exc

    if "rates" in payload and isinstance(payload["rates"], dict):
        if all(isinstance(value, (int, float)) for value in payload["rates"].values()):
            return {str(payload.get("date") or end.isoformat()): payload["rates"]}
        return payload["rates"]

    raise MarketDataError("Exchange-rate API response shape is invalid.")


def convert_usd_rates_to_pairs(
    rates_by_date: dict[str, dict[str, float]],
) -> dict[str, list[dict[str, Any]]]:
    series = {pair["key"]: [] for pair in EXCHANGE_PAIRS}

    for day in sorted(rates_by_date):
        row = rates_by_date[day]
        krw = _to_float(row.get("KRW"))
        jpy = _to_float(row.get("JPY"))
        eur = _to_float(row.get("EUR"))

        if krw is not None:
            series["USD_KRW"].append({"date": day, "rate": krw})
        if krw is not None and jpy not in (None, 0):
            series["JPY_KRW"].append({"date": day, "rate": krw / jpy})
        if krw is not None and eur not in (None, 0):
            series["EUR_KRW"].append({"date": day, "rate": krw / eur})

    return series


def latest_rate(history: list[dict[str, Any]]) -> float | None:
    if not history:
        return None
    return history[-1]["rate"]


def rate_change(history: list[dict[str, Any]]) -> float | None:
    if len(history) < 2:
        return None
    return history[-1]["rate"] - history[-2]["rate"]


def rate_change_percent(history: list[dict[str, Any]]) -> float | None:
    if len(history) < 2 or history[-2]["rate"] == 0:
        return None
    return (history[-1]["rate"] - history[-2]["rate"]) / abs(history[-2]["rate"])


def exchange_date_range(period: str) -> tuple[date, date]:
    end = date.today()
    start = end - timedelta(days=EXCHANGE_PERIOD_DAYS[normalize_period(period)])
    return start, end


def normalize_period(period: str) -> str:
    value = (period or "1m").lower()
    if value in PERIODS:
        return value
    return "1m"


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
