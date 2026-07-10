"""Compatibility wrapper for the legacy SEC financial analysis API."""

from __future__ import annotations

from typing import Any

from .analysis_presets import DEFAULT_THRESHOLDS, MetricThreshold
from .metric_calculator import (
    SUITABLE_THRESHOLD,
    analyze_normalized_financials,
    format_percent,
    growth_rate,
    is_usable_number,
    normalize_legacy_sec_rows,
    safe_divide,
)


class AnalysisError(RuntimeError):
    """Raised when financial rows cannot be analyzed safely."""


MetricRule = MetricThreshold
METRIC_RULES = DEFAULT_THRESHOLDS


def analyze_financials(financial_rows: list[dict[str, Any]]) -> dict[str, Any]:
    try:
        normalized = normalize_legacy_sec_rows(financial_rows, currency="USD")
        result = analyze_normalized_financials(normalized, preset_id="default")
    except ValueError as exc:
        raise AnalysisError(str(exc)) from exc

    if all(summary["valid_count"] == 0 for summary in result["summaries"]):
        raise AnalysisError("계산 가능한 재무 지표가 없습니다. SEC companyfacts 태그를 확인하세요.")

    return result


def calculate_annual_metrics(financial_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = normalize_legacy_sec_rows(financial_rows, currency="USD")
    return analyze_normalized_financials(normalized, preset_id="default")["annual_rows"]


def summarize_metrics(annual_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from .analysis_presets import PRESETS
    from .metric_calculator import summarize_metrics as summarize_common

    return summarize_common(annual_rows, PRESETS["default"])


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if value == "":
                return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if is_usable_number(number) else None
