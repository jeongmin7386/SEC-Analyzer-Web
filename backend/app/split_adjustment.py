"""Stock split adjustment for SEC annual share and EPS facts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


SHARE_FIELDS = ("WeightedAverageNumberOfSharesOutstanding",)
EPS_FIELDS = ("EarningsPerShareBasic",)


@dataclass(frozen=True)
class StockSplit:
    date: date
    ratio: float


def apply_split_adjustments(
    financial_rows: list[dict[str, Any]],
    splits: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    normalized_splits = normalize_splits(splits)
    if not financial_rows or not normalized_splits:
        return financial_rows, []

    row_dates = [row_date for row in financial_rows if (row_date := parse_row_date(row))]
    if not row_dates:
        return financial_rows, []

    latest_row_date = max(row_dates)
    adjusted_rows: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []

    for row in financial_rows:
        row_date = parse_row_date(row)
        factor = cumulative_split_factor(row_date, latest_row_date, normalized_splits)
        if factor == 1:
            adjusted_rows.append(row)
            continue

        adjusted = dict(row)
        for field in SHARE_FIELDS:
            adjusted[field] = multiply_number(adjusted.get(field), factor)
        for field in EPS_FIELDS:
            adjusted[field] = divide_number(adjusted.get(field), factor)
        adjusted["split_adjustment_factor"] = factor
        adjusted_rows.append(adjusted)
        applied.append(
            {
                "fiscalYear": adjusted.get("fiscal_year"),
                "date": adjusted.get("date"),
                "factor": factor,
            }
        )

    return adjusted_rows, applied


def normalize_splits(splits: list[dict[str, Any]]) -> list[StockSplit]:
    normalized: list[StockSplit] = []
    for item in splits:
        split_date = parse_date(item.get("date"))
        ratio = to_float(item.get("ratio"))
        if split_date is None or ratio is None or ratio <= 0 or ratio == 1:
            continue
        normalized.append(StockSplit(date=split_date, ratio=ratio))
    return sorted(normalized, key=lambda split: split.date)


def cumulative_split_factor(
    row_date: date | None,
    latest_row_date: date,
    splits: list[StockSplit],
) -> float:
    if row_date is None:
        return 1.0

    factor = 1.0
    for split in splits:
        if row_date < split.date <= latest_row_date:
            factor *= split.ratio
    return factor


def parse_row_date(row: dict[str, Any]) -> date | None:
    parsed = parse_date(row.get("date"))
    if parsed is not None:
        return parsed

    year = row.get("fiscal_year")
    try:
        return date(int(year), 12, 31)
    except (TypeError, ValueError):
        return None


def parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None

    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def multiply_number(value: Any, factor: float) -> float | None:
    number = to_float(value)
    if number is None:
        return None
    return number * factor


def divide_number(value: Any, factor: float) -> float | None:
    number = to_float(value)
    if number is None or factor == 0:
        return None
    return number / factor


def to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
