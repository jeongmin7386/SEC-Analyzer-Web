"""Common financial metric calculation for normalized stock data."""

from __future__ import annotations

from math import isfinite
from statistics import fmean, stdev
from typing import Any

from .analysis_presets import AnalysisPreset, MetricThreshold, get_preset


SUITABLE_THRESHOLD = 3.0
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
PASS = "PASS"
FAIL = "FAIL"


def analyze_normalized_financials(
    financials: list[dict[str, Any]],
    preset_id: str | None = "default",
    industry: str | None = None,
) -> dict[str, Any]:
    if not financials:
        raise ValueError("분석할 재무 데이터가 없습니다.")

    preset = get_preset(preset_id)
    annual_rows = calculate_annual_metrics(financials)
    metric_rows = summarize_metrics(annual_rows, preset, industry=industry)

    average_score = sum(row["average_score"] for row in metric_rows)
    stability_score = sum(row["stability_score"] for row in metric_rows)
    total_score = stability_score

    return {
        "annual_rows": annual_rows,
        "summaries": metric_rows,
        "metric_rows": metric_rows,
        "metrics": metric_rows,
        "score": {
            "averageScore": average_score,
            "stabilityScore": stability_score,
            "totalScore": total_score,
            "maxScore": float(len(preset.thresholds)),
            "isSuitable": total_score >= SUITABLE_THRESHOLD,
            "verdict": "적합" if total_score >= SUITABLE_THRESHOLD else "부적합",
            "presetId": preset.id,
            "presetName": preset.name,
        },
        "average_score": average_score,
        "stability_score": stability_score,
        "total_score": total_score,
        "average_is_suitable": average_score >= SUITABLE_THRESHOLD,
        "stability_is_suitable": stability_score >= SUITABLE_THRESHOLD,
        "is_suitable": total_score >= SUITABLE_THRESHOLD,
    }


def normalize_legacy_sec_rows(
    rows: list[dict[str, Any]],
    currency: str = "USD",
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        normalized.append(
            {
                "fiscalYear": _to_int(row.get("fiscalYear") or row.get("fiscal_year")),
                "periodType": "ANNUAL",
                "currency": currency,
                "revenue": _to_float(row.get("revenue") or row.get("Revenue")),
                "netIncome": _to_float(row.get("netIncome") or row.get("NetIncomeLoss")),
                "totalAssets": _to_float(row.get("totalAssets") or row.get("Assets")),
                "totalLiabilities": _to_float(row.get("totalLiabilities") or row.get("Liabilities")),
                "totalEquity": _to_float(row.get("totalEquity") or row.get("StockholdersEquity")),
                "currentAssets": _to_float(row.get("currentAssets") or row.get("AssetsCurrent")),
                "currentLiabilities": _to_float(
                    row.get("currentLiabilities") or row.get("LiabilitiesCurrent")
                ),
                "sharesOutstanding": _to_float(
                    row.get("sharesOutstanding")
                    or row.get("WeightedAverageNumberOfSharesOutstanding")
                ),
                "eps": _to_float(row.get("eps") or row.get("EarningsPerShareBasic")),
                "filedAt": row.get("filedAt") or row.get("date"),
                "sourceType": row.get("sourceType") or "SEC",
                "sourceUrl": row.get("sourceUrl"),
                "metadata": row.get("metadata") or {},
            }
        )
    return [row for row in normalized if row.get("fiscalYear") is not None]


def calculate_annual_metrics(financials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None

    for row in sorted(financials, key=lambda item: item.get("fiscalYear") or 0):
        revenue = _to_float(row.get("revenue"))
        net_income = _to_float(row.get("netIncome"))
        liabilities = _to_float(row.get("totalLiabilities"))
        equity = _to_float(row.get("totalEquity"))
        current_assets = _to_float(row.get("currentAssets"))
        current_liabilities = _to_float(row.get("currentLiabilities"))
        shares_out = _to_float(row.get("sharesOutstanding"))
        eps = _to_float(row.get("eps"))

        metrics = {
            **row,
            "fiscal_year": row.get("fiscalYear"),
            "date": row.get("filedAt"),
            "Revenue": revenue,
            "NetIncomeLoss": net_income,
            "Assets": _to_float(row.get("totalAssets")),
            "Liabilities": liabilities,
            "StockholdersEquity": equity,
            "AssetsCurrent": current_assets,
            "LiabilitiesCurrent": current_liabilities,
            "WeightedAverageNumberOfSharesOutstanding": shares_out,
            "EarningsPerShareBasic": eps,
            "net_profit_margin": safe_divide(net_income, revenue),
            "net_income_growth": None,
            "debt_ratio": safe_divide(liabilities, equity),
            "current_ratio": safe_divide(current_assets, current_liabilities),
            "roe": safe_divide(net_income, equity),
            "share_retirement_rate": None,
            "share_issuance_rate": None,
            "eps_growth": None,
        }

        if previous is not None:
            metrics["net_income_growth"] = growth_rate(net_income, previous["NetIncomeLoss"])
            share_growth = growth_rate(
                shares_out,
                previous["WeightedAverageNumberOfSharesOutstanding"],
            )
            metrics["share_retirement_rate"] = -share_growth if share_growth is not None else None
            metrics["share_issuance_rate"] = abs(share_growth) if share_growth is not None else None
            metrics["eps_growth"] = growth_rate(eps, previous["EarningsPerShareBasic"])

        rows.append(metrics)
        previous = metrics

    return rows


def summarize_metrics(
    annual_rows: list[dict[str, Any]],
    preset: AnalysisPreset,
    industry: str | None = None,
) -> list[dict[str, Any]]:
    excluded = excluded_metric_keys(industry)
    summaries: list[dict[str, Any]] = []

    for rule in preset.thresholds:
        values = [
            value
            for row in annual_rows
            if is_usable_number(value := row.get(rule.key))
        ]
        average = fmean(values) if values else None
        deviation = stdev(values) if len(values) > 1 else (0.0 if values else None)
        adjusted_value = adjusted_metric_value(average, deviation, rule)

        if rule.key in excluded:
            status = INSUFFICIENT_DATA
            note = "금융업은 일반 기업용 부채/유동성 기준 평가에서 제외됩니다."
            average_pass = False
            stability_score = 0.0
        else:
            status = metric_status(average, rule)
            note = None
            average_pass = status == PASS
            stability_score = score_metric(average, deviation, rule)

        stability_pass = stability_score >= 1.0
        average_score = 1.0 if average_pass else 0.0

        summaries.append(
            {
                "key": rule.key,
                "name": rule.name,
                "threshold": threshold_label(rule),
                "thresholdValue": rule.threshold,
                "direction": rule.direction,
                "metric_type": "positive" if rule.direction == "higher" else "negative",
                "mean": average,
                "std": deviation,
                "average": average,
                "stdev": deviation,
                "adjusted_value": adjusted_value,
                "average_plus_sd": (
                    average + deviation
                    if average is not None and deviation is not None
                    else None
                ),
                "average_pass": average_pass,
                "stability_pass": stability_pass,
                "average_score": average_score,
                "stability_score": stability_score,
                "pass_value": int(average_pass),
                "score": stability_score,
                "valid_count": len(values),
                "status": status,
                "judgement": status,
                "note": note,
            }
        )

    return summaries


def adjusted_metric_value(
    average: float | None,
    deviation: float | None,
    rule: MetricThreshold,
) -> float | None:
    if average is None or deviation is None:
        return None
    return average - deviation if rule.direction == "higher" else average + deviation


def metric_status(value: float | None, rule: MetricThreshold) -> str:
    if value is None:
        return INSUFFICIENT_DATA
    if rule.direction == "higher":
        return PASS if value >= rule.threshold else FAIL
    return PASS if value < rule.threshold else FAIL


def score_metric(average: float | None, deviation: float | None, rule: MetricThreshold) -> float:
    if average is None or deviation is None:
        return 0.0

    if rule.direction == "higher":
        if average - deviation >= rule.threshold:
            return 1.0
        if average >= rule.threshold:
            return 0.5
        return 0.0

    if average + deviation < rule.threshold:
        return 1.0
    if average < rule.threshold:
        return 0.5
    return 0.0


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if not is_usable_number(numerator) or not is_usable_number(denominator):
        return None
    if denominator <= 0:
        return None
    result = numerator / denominator
    return result if is_usable_number(result) else None


def growth_rate(current: float | None, previous: float | None) -> float | None:
    if not is_usable_number(current) or not is_usable_number(previous):
        return None
    if previous <= 0:
        return None
    result = (current - previous) / abs(previous)
    return result if is_usable_number(result) else None


def is_usable_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def threshold_label(rule: MetricThreshold) -> str:
    operator = ">=" if rule.direction == "higher" else "<"
    return f"{operator} {format_percent(rule.threshold)}"


def format_percent(value: float | None) -> str:
    if not is_usable_number(value):
        return "N/A"
    return f"{value * 100:.2f}%"


def excluded_metric_keys(industry: str | None) -> set[str]:
    value = (industry or "").lower()
    finance_terms = ("bank", "financial", "insurance", "securities", "금융", "은행", "보험", "증권")
    if any(term in value for term in finance_terms):
        return {"debt_ratio", "current_ratio"}
    return set()


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if not value:
                return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if is_usable_number(number) else None


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
