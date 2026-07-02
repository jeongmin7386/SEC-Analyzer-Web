"""Financial statement analysis and scoring logic for SEC EDGAR facts."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from statistics import fmean, stdev
from typing import Any, Literal


Direction = Literal["higher", "lower"]


class AnalysisError(RuntimeError):
    """Raised when financial rows cannot be analyzed safely."""


@dataclass(frozen=True)
class MetricRule:
    key: str
    name: str
    threshold: float
    direction: Direction

    @property
    def threshold_label(self) -> str:
        operator = ">=" if self.direction == "higher" else "<"
        return f"{operator} {format_percent(self.threshold)}"


METRIC_RULES: tuple[MetricRule, ...] = (
    MetricRule("net_profit_margin", "당기 순이익률", 0.20, "higher"),
    MetricRule("net_income_growth", "순이익 성장률", 0.10, "higher"),
    MetricRule("debt_ratio", "부채 비율", 0.75, "lower"),
    MetricRule("current_ratio", "유동 비율", 1.00, "higher"),
    MetricRule("roe", "ROE", 0.25, "higher"),
    MetricRule("share_issuance_rate", "주식 발행률", 0.10, "lower"),
    MetricRule("eps_growth", "주당 순이익률", 0.075, "higher"),
)


def analyze_financials(financial_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not financial_rows:
        raise AnalysisError("분석할 재무 데이터가 없습니다.")

    annual_rows = calculate_annual_metrics(financial_rows)
    if not annual_rows:
        raise AnalysisError("계산 가능한 연간 재무 데이터가 없습니다.")

    summaries = summarize_metrics(annual_rows)
    if all(summary["valid_count"] == 0 for summary in summaries):
        raise AnalysisError("계산 가능한 지표가 없습니다. SEC companyfacts 태그를 확인하세요.")

    average_score = sum(summary["average_score"] for summary in summaries)
    stability_score = sum(summary["stability_score"] for summary in summaries)

    return {
        "annual_rows": annual_rows,
        "summaries": summaries,
        "average_score": average_score,
        "stability_score": stability_score,
        "total_score": stability_score,
        "average_is_suitable": average_score >= 3,
        "stability_is_suitable": stability_score >= 3,
        "is_suitable": stability_score >= 3,
    }


def calculate_annual_metrics(financial_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    previous: dict[str, Any] | None = None

    for index, row in enumerate(financial_rows, start=1):
        if not isinstance(row, dict):
            raise AnalysisError(f"{index}번째 재무 데이터의 형식이 올바르지 않습니다.")

        revenue = to_float(row.get("Revenue"))
        net_income = to_float(row.get("NetIncomeLoss"))
        assets = to_float(row.get("Assets"))
        liabilities = to_float(row.get("Liabilities"))
        equity = to_float(row.get("StockholdersEquity"))
        current_assets = to_float(row.get("AssetsCurrent"))
        current_liabilities = to_float(row.get("LiabilitiesCurrent"))
        shares_out = to_float(row.get("WeightedAverageNumberOfSharesOutstanding"))
        eps = to_float(row.get("EarningsPerShareBasic"))

        metrics = {
            "fiscal_year": row.get("fiscal_year") or _year_from_date(row.get("date")),
            "date": row.get("date"),
            "Revenue": revenue,
            "NetIncomeLoss": net_income,
            "Assets": assets,
            "Liabilities": liabilities,
            "StockholdersEquity": equity,
            "AssetsCurrent": current_assets,
            "LiabilitiesCurrent": current_liabilities,
            "WeightedAverageNumberOfSharesOutstanding": shares_out,
            "EarningsPerShareBasic": eps,
            "net_profit_margin": safe_divide(net_income, revenue),
            "net_income_growth": None,
            "debt_ratio": debt_ratio(liabilities, assets, equity),
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
            metrics["share_retirement_rate"] = (
                -share_growth if share_growth is not None else None
            )
            metrics["share_issuance_rate"] = (
                max(share_growth, 0.0) if share_growth is not None else None
            )
            metrics["eps_growth"] = growth_rate(eps, previous["EarningsPerShareBasic"])

        rows.append(metrics)
        previous = metrics

    return rows


def summarize_metrics(annual_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []

    for rule in METRIC_RULES:
        values = [
            value
            for row in annual_rows
            if is_usable_number(value := row.get(rule.key))
        ]
        average = fmean(values) if values else None
        deviation = stdev(values) if len(values) > 1 else (0.0 if values else None)
        adjusted_value = adjusted_metric_value(average, deviation, rule)
        average_pass = metric_pass(average, rule)
        stability_pass = metric_pass(adjusted_value, rule)
        average_score = 1.0 if average_pass else 0.0
        stability_score = 1.0 if stability_pass else 0.0

        summaries.append(
            {
                "key": rule.key,
                "name": rule.name,
                "threshold": rule.threshold_label,
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
                "judgement": judgement_label(stability_score),
            }
        )

    return summaries


def adjusted_metric_value(
    average: float | None,
    deviation: float | None,
    rule: MetricRule,
) -> float | None:
    if average is None or deviation is None:
        return None

    if rule.direction == "higher":
        return average - deviation

    return average + deviation


def metric_pass(value: float | None, rule: MetricRule) -> bool:
    if value is None:
        return False

    if rule.direction == "higher":
        return value >= rule.threshold

    return value < rule.threshold


def score_metric(average: float | None, deviation: float | None, rule: MetricRule) -> float:
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


def judgement_label(score: float) -> str:
    if score == 1.0:
        return "통과"
    if score == 0.5:
        return "주의"
    return "미달"


def safe_divide(numerator: float | None, denominator: float | None) -> float | None:
    if not is_usable_number(numerator) or not is_usable_number(denominator) or denominator == 0:
        return None

    result = numerator / denominator
    return result if is_usable_number(result) else None


def debt_ratio(
    liabilities: float | None,
    assets: float | None,
    equity: float | None,
) -> float | None:
    direct = safe_divide(liabilities, assets)
    if direct is not None:
        return direct

    if is_usable_number(liabilities) and is_usable_number(equity):
        return safe_divide(liabilities, liabilities + equity)

    return None


def growth_rate(current: float | None, previous: float | None) -> float | None:
    if not is_usable_number(current) or not is_usable_number(previous) or previous == 0:
        return None

    result = (current - previous) / abs(previous)
    return result if is_usable_number(result) else None


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


def is_usable_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def format_percent(value: float | None) -> str:
    if not is_usable_number(value):
        return "N/A"
    return f"{value * 100:.2f}%"


def _year_from_date(value: Any) -> str | None:
    if isinstance(value, str) and len(value) >= 4:
        return value[:4]
    return None
