"""Small stock master data used by the market resolver.

The Korean master is intentionally file/code based for now because OpenDART
corp_code.zip requires an API key. The structure keeps the replacement path
simple: load the same fields from a cached master file later.
"""

from __future__ import annotations

from typing import Any


KR_STOCK_MASTER: tuple[dict[str, Any], ...] = (
    {
        "market": "KR",
        "symbol": "005930",
        "displaySymbol": "005930",
        "companyName": "삼성전자",
        "englishName": "Samsung Electronics",
        "exchange": "KOSPI",
        "currency": "KRW",
        "corpCode": "00126380",
        "priceSymbol": "005930.KS",
        "aliases": ("samsung", "samsung electronics", "삼전"),
    },
    {
        "market": "KR",
        "symbol": "000660",
        "displaySymbol": "000660",
        "companyName": "SK하이닉스",
        "englishName": "SK hynix",
        "exchange": "KOSPI",
        "currency": "KRW",
        "corpCode": "00164779",
        "priceSymbol": "000660.KS",
        "aliases": ("sk hynix", "hynix", "하이닉스"),
    },
    {
        "market": "KR",
        "symbol": "035720",
        "displaySymbol": "035720",
        "companyName": "카카오",
        "englishName": "Kakao",
        "exchange": "KOSPI",
        "currency": "KRW",
        "corpCode": "00258801",
        "priceSymbol": "035720.KS",
        "aliases": ("kakao",),
    },
    {
        "market": "KR",
        "symbol": "035420",
        "displaySymbol": "035420",
        "companyName": "NAVER",
        "englishName": "NAVER",
        "exchange": "KOSPI",
        "currency": "KRW",
        "corpCode": "00266961",
        "priceSymbol": "035420.KS",
        "aliases": ("naver", "네이버"),
    },
    {
        "market": "KR",
        "symbol": "005380",
        "displaySymbol": "005380",
        "companyName": "현대차",
        "englishName": "Hyundai Motor",
        "exchange": "KOSPI",
        "currency": "KRW",
        "corpCode": "00164742",
        "priceSymbol": "005380.KS",
        "aliases": ("hyundai", "hyundai motor"),
    },
)


def normalize_kr_symbol(value: str) -> str:
    symbol = str(value or "").strip().upper()
    if symbol.endswith(".KS") or symbol.endswith(".KQ"):
        symbol = symbol[:-3]
    return symbol


def get_kr_stock(symbol: str) -> dict[str, Any] | None:
    normalized = normalize_kr_symbol(symbol)
    for stock in KR_STOCK_MASTER:
        if stock["symbol"] == normalized:
            return dict(stock)
    return None


def search_kr_stocks(query: str, limit: int = 10) -> list[dict[str, Any]]:
    normalized_query = normalize_kr_symbol(query)
    lowered = normalized_query.lower()
    if not lowered:
        return []

    results: list[tuple[int, dict[str, Any]]] = []
    for stock in KR_STOCK_MASTER:
        haystack = [
            stock["symbol"],
            stock["companyName"],
            stock.get("englishName", ""),
            stock.get("exchange", ""),
            *(stock.get("aliases") or ()),
        ]
        haystack_lower = [str(value).lower() for value in haystack if value]

        if stock["symbol"] == normalized_query:
            rank = 0
        elif any(value == lowered for value in haystack_lower):
            rank = 1
        elif any(lowered in value for value in haystack_lower):
            rank = 2
        else:
            continue

        results.append((rank, public_stock(stock)))

    return [item for _, item in sorted(results, key=lambda pair: (pair[0], pair[1]["symbol"]))[:limit]]


def public_stock(stock: dict[str, Any]) -> dict[str, Any]:
    return {
        "market": "KR",
        "symbol": stock["symbol"],
        "displaySymbol": stock["displaySymbol"],
        "companyName": stock["companyName"],
        "exchange": stock["exchange"],
        "currency": "KRW",
        "corpCode": stock.get("corpCode"),
        "priceSymbol": stock.get("priceSymbol"),
    }
