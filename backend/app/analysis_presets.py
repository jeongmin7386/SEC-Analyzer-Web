"""Analysis preset configuration shared by US and Korean stock analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MarketName = Literal["KR", "US", "ALL"]
Direction = Literal["higher", "lower"]


@dataclass(frozen=True)
class MetricThreshold:
    key: str
    name: str
    threshold: float
    direction: Direction


@dataclass(frozen=True)
class AnalysisPreset:
    id: str
    name: str
    market: MarketName
    thresholds: tuple[MetricThreshold, ...]


DEFAULT_THRESHOLDS: tuple[MetricThreshold, ...] = (
    MetricThreshold("net_profit_margin", "당기순이익률", 0.20, "higher"),
    MetricThreshold("net_income_growth", "순이익 성장률", 0.10, "higher"),
    MetricThreshold("debt_ratio", "부채비율", 0.75, "lower"),
    MetricThreshold("current_ratio", "유동비율", 1.00, "higher"),
    MetricThreshold("roe", "ROE", 0.25, "higher"),
    MetricThreshold("share_issuance_rate", "주식발행 증가율", 0.10, "lower"),
    MetricThreshold("eps_growth", "EPS 성장률", 0.075, "higher"),
)


PRESETS: dict[str, AnalysisPreset] = {
    "default": AnalysisPreset("default", "기본 분석", "ALL", DEFAULT_THRESHOLDS),
    "kr-market": AnalysisPreset(
        "kr-market",
        "한국 시장",
        "KR",
        (
            MetricThreshold("net_profit_margin", "당기순이익률", 0.08, "higher"),
            MetricThreshold("net_income_growth", "순이익 성장률", 0.05, "higher"),
            MetricThreshold("debt_ratio", "부채비율", 1.50, "lower"),
            MetricThreshold("current_ratio", "유동비율", 1.00, "higher"),
            MetricThreshold("roe", "ROE", 0.10, "higher"),
            MetricThreshold("share_issuance_rate", "주식발행 증가율", 0.10, "lower"),
            MetricThreshold("eps_growth", "EPS 성장률", 0.05, "higher"),
        ),
    ),
    "us-growth": AnalysisPreset(
        "us-growth",
        "미국 성장주",
        "US",
        (
            MetricThreshold("net_profit_margin", "당기순이익률", 0.20, "higher"),
            MetricThreshold("net_income_growth", "순이익 성장률", 0.15, "higher"),
            MetricThreshold("debt_ratio", "부채비율", 0.75, "lower"),
            MetricThreshold("current_ratio", "유동비율", 1.00, "higher"),
            MetricThreshold("roe", "ROE", 0.25, "higher"),
            MetricThreshold("share_issuance_rate", "주식발행 증가율", 0.08, "lower"),
            MetricThreshold("eps_growth", "EPS 성장률", 0.10, "higher"),
        ),
    ),
    "custom": AnalysisPreset("custom", "사용자 설정", "ALL", DEFAULT_THRESHOLDS),
}


def get_preset(preset_id: str | None) -> AnalysisPreset:
    return PRESETS.get((preset_id or "default").strip(), PRESETS["default"])
