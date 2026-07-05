"""ETF holdings lookup helpers.

The SEC companyfacts API does not provide ETF constituent holdings. This module
keeps that boundary explicit so a real holdings provider can replace the sample
data later without changing the analyzer.
"""

from __future__ import annotations

from typing import Any


class ETFHoldingsError(ValueError):
    """Raised when ETF holdings cannot be resolved or parsed."""


SAMPLE_ETF_HOLDINGS: dict[str, list[dict[str, Any]]] = {
    "SPY": [
        {"ticker": "MSFT", "name": "Microsoft Corp.", "weight": 0.073},
        {"ticker": "AAPL", "name": "Apple Inc.", "weight": 0.062},
        {"ticker": "NVDA", "name": "NVIDIA Corp.", "weight": 0.058},
        {"ticker": "AMZN", "name": "Amazon.com Inc.", "weight": 0.038},
        {"ticker": "META", "name": "Meta Platforms Inc.", "weight": 0.026},
        {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "weight": 0.021},
        {"ticker": "BRK.B", "name": "Berkshire Hathaway Inc. Class B", "weight": 0.018},
        {"ticker": "GOOG", "name": "Alphabet Inc. Class C", "weight": 0.017},
        {"ticker": "AVGO", "name": "Broadcom Inc.", "weight": 0.016},
        {"ticker": "TSLA", "name": "Tesla Inc.", "weight": 0.015},
    ],
    "QQQ": [
        {"ticker": "MSFT", "name": "Microsoft Corp.", "weight": 0.087},
        {"ticker": "AAPL", "name": "Apple Inc.", "weight": 0.083},
        {"ticker": "NVDA", "name": "NVIDIA Corp.", "weight": 0.078},
        {"ticker": "AMZN", "name": "Amazon.com Inc.", "weight": 0.055},
        {"ticker": "META", "name": "Meta Platforms Inc.", "weight": 0.049},
        {"ticker": "AVGO", "name": "Broadcom Inc.", "weight": 0.045},
        {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "weight": 0.029},
        {"ticker": "GOOG", "name": "Alphabet Inc. Class C", "weight": 0.028},
        {"ticker": "TSLA", "name": "Tesla Inc.", "weight": 0.026},
        {"ticker": "COST", "name": "Costco Wholesale Corp.", "weight": 0.024},
    ],
    "IVV": [
        {"ticker": "MSFT", "name": "Microsoft Corp.", "weight": 0.073},
        {"ticker": "AAPL", "name": "Apple Inc.", "weight": 0.062},
        {"ticker": "NVDA", "name": "NVIDIA Corp.", "weight": 0.058},
        {"ticker": "AMZN", "name": "Amazon.com Inc.", "weight": 0.038},
        {"ticker": "META", "name": "Meta Platforms Inc.", "weight": 0.026},
        {"ticker": "GOOGL", "name": "Alphabet Inc. Class A", "weight": 0.021},
        {"ticker": "BRK.B", "name": "Berkshire Hathaway Inc. Class B", "weight": 0.018},
        {"ticker": "GOOG", "name": "Alphabet Inc. Class C", "weight": 0.017},
        {"ticker": "AVGO", "name": "Broadcom Inc.", "weight": 0.016},
        {"ticker": "TSLA", "name": "Tesla Inc.", "weight": 0.015},
    ],
}


def get_etf_holdings(etf_ticker: str) -> list[dict[str, Any]]:
    """Return top ETF holdings from the temporary sample dictionary."""

    symbol = normalize_symbol(etf_ticker)
    holdings = SAMPLE_ETF_HOLDINGS.get(symbol)
    if holdings is None:
        raise ETFHoldingsError(
            f"{symbol} holdings are not available yet. Enter holdings manually, for example: "
            "AAPL:7.5, MSFT:7.2, NVDA:6.8"
        )

    return [dict(holding) for holding in holdings[:10]]


def parse_manual_holdings(raw_value: str) -> list[dict[str, Any]]:
    """Parse manual holdings like 'AAPL:7.5, MSFT:7.2' into decimal weights."""

    raw_value = (raw_value or "").strip()
    if not raw_value:
        raise ETFHoldingsError("Enter at least one holding, for example: AAPL:7.5, MSFT:7.2")

    holdings: list[dict[str, Any]] = []
    normalized = raw_value.replace("\n", ",").replace(";", ",")
    for index, part in enumerate(normalized.split(","), start=1):
        item = part.strip()
        if not item:
            continue

        if ":" not in item:
            raise ETFHoldingsError(f"Manual holding #{index} must use ticker:weight format.")

        ticker_part, weight_part = item.split(":", 1)
        ticker = normalize_symbol(ticker_part)
        weight = normalize_weight(weight_part)
        holdings.append({"ticker": ticker, "name": ticker, "weight": weight})

    if not holdings:
        raise ETFHoldingsError("No valid holdings were entered.")

    return holdings[:10]


def normalize_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper()
    if not symbol:
        raise ETFHoldingsError("Ticker is required.")
    if len(symbol) > 16 or not all(character.isalnum() or character in ".-" for character in symbol):
        raise ETFHoldingsError(f"Invalid ticker format: {symbol}")
    return symbol


def normalize_weight(value: Any) -> float:
    try:
        number = float(str(value).strip().replace("%", ""))
    except (TypeError, ValueError) as exc:
        raise ETFHoldingsError(f"Invalid holding weight: {value}") from exc

    if number <= 0:
        raise ETFHoldingsError("Holding weights must be greater than 0.")
    if number > 100:
        raise ETFHoldingsError("Holding weights cannot exceed 100%.")
    if number > 1:
        return number / 100
    return number
