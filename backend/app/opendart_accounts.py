"""OpenDART account mapping to normalized financial fields."""

from __future__ import annotations

import re
from typing import Any


ACCOUNT_MAP: dict[str, dict[str, tuple[str, ...]]] = {
    "revenue": {
        "ids": (
            "ifrs-full_Revenue",
            "ifrs-full_RevenueFromContractsWithCustomers",
            "dart_OperatingRevenue",
        ),
        "aliases": ("매출액", "수익(매출액)", "영업수익", "매출"),
    },
    "operatingIncome": {
        "ids": ("dart_OperatingIncomeLoss",),
        "aliases": ("영업이익", "영업손익"),
    },
    "netIncome": {
        "ids": (
            "ifrs-full_ProfitLoss",
            "ifrs-full_ProfitLossAttributableToOwnersOfParent",
        ),
        "aliases": ("당기순이익", "당기순손익", "연결당기순이익", "지배기업 소유주지분 순이익"),
    },
    "totalAssets": {
        "ids": ("ifrs-full_Assets",),
        "aliases": ("자산총계", "자산 총계"),
    },
    "totalLiabilities": {
        "ids": ("ifrs-full_Liabilities",),
        "aliases": ("부채총계", "부채 총계"),
    },
    "totalEquity": {
        "ids": ("ifrs-full_Equity", "ifrs-full_EquityAttributableToOwnersOfParent"),
        "aliases": ("자본총계", "자본 총계", "지배기업 소유주지분"),
    },
    "currentAssets": {
        "ids": ("ifrs-full_CurrentAssets",),
        "aliases": ("유동자산",),
    },
    "currentLiabilities": {
        "ids": ("ifrs-full_CurrentLiabilities",),
        "aliases": ("유동부채",),
    },
    "sharesOutstanding": {
        "ids": ("dart_NumberOfIssuedShares", "dart_IssuedShareCapital"),
        "aliases": ("발행주식수", "보통주 발행주식수"),
    },
    "eps": {
        "ids": ("ifrs-full_BasicEarningsLossPerShare",),
        "aliases": ("기본주당이익", "기본주당순이익", "기본주당손익"),
    },
    "operatingCashFlow": {
        "ids": ("ifrs-full_CashFlowsFromUsedInOperatingActivities",),
        "aliases": ("영업활동현금흐름", "영업활동으로 인한 현금흐름"),
    },
}


def normalize_dart_statement(
    rows: list[dict[str, Any]],
    *,
    fiscal_year: int,
    currency: str = "KRW",
    fs_div: str,
) -> dict[str, Any]:
    normalized: dict[str, Any] = {
        "fiscalYear": fiscal_year,
        "periodType": "ANNUAL",
        "currency": currency,
        "sourceType": "OPENDART",
        "metadata": {
            "fsDiv": fs_div,
            "reportCode": "11011",
            "unit": "KRW",
            "accounts": {},
        },
    }

    for field, mapping in ACCOUNT_MAP.items():
        match = find_account(rows, mapping)
        if match is None:
            normalized[field] = None
            continue

        normalized[field] = parse_amount(match.get("thstrm_amount"))
        normalized["metadata"]["accounts"][field] = {
            "accountId": match.get("account_id"),
            "accountName": match.get("account_nm"),
            "statementName": match.get("sj_nm"),
            "statementDiv": match.get("sj_div"),
            "fsDiv": match.get("fs_div") or fs_div,
            "currency": match.get("currency") or currency,
        }

    return normalized


def find_account(
    rows: list[dict[str, Any]],
    mapping: dict[str, tuple[str, ...]],
) -> dict[str, Any] | None:
    wanted_ids = set(mapping.get("ids", ()))
    wanted_aliases = {normalize_name(alias) for alias in mapping.get("aliases", ())}

    for row in rows:
        if row.get("account_id") in wanted_ids:
            return row

    for row in rows:
        account_name = normalize_name(row.get("account_nm"))
        if account_name in wanted_aliases:
            return row

    for row in rows:
        account_name = normalize_name(row.get("account_nm"))
        if any(alias and alias in account_name for alias in wanted_aliases):
            return row

    return None


def parse_amount(value: Any) -> float | None:
    if value in (None, ""):
        return None

    text = str(value).strip().replace(",", "")
    if text in {"-", ""}:
        return None

    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]

    try:
        number = float(text)
    except ValueError:
        return None

    return -number if negative else number


def normalize_name(value: Any) -> str:
    text = str(value or "").lower()
    return re.sub(r"[\s()\[\]ㆍ·_-]+", "", text)
