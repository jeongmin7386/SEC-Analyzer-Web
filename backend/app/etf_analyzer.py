"""ETF scoring based on constituent SEC analyses."""

from __future__ import annotations

from typing import Any

from .analyzer import AnalysisError, analyze_financials
from .sec_client import SECClient, SECClientError


SUITABLE_THRESHOLD = 3.0


def analyze_etf(
    etf_ticker: str,
    holdings: list[dict[str, Any]],
    sec_client: SECClient,
    limit: int = 10,
) -> dict[str, Any]:
    """Analyze ETF holdings without treating the ETF itself as a company."""

    symbol = etf_ticker.strip().upper()
    holding_rows: list[dict[str, Any]] = []
    score_sum = 0.0
    weighted_score_sum = 0.0
    weight_sum = 0.0
    success_count = 0
    cache_hit_count = 0

    for holding in holdings[:10]:
        holding_symbol = str(holding.get("ticker", "")).strip().upper()
        holding_name = str(holding.get("name") or holding_symbol)
        holding_weight = float(holding.get("weight") or 0.0)

        row = {
            "etfTicker": symbol,
            "ticker": holding_symbol,
            "name": holding_name,
            "weight": holding_weight,
            "companyScore": None,
            "companyVerdict": None,
            "analysisSuccess": False,
            "failureReason": "",
            "cache": None,
        }

        try:
            sec_result = sec_client.fetch_annual_financials(holding_symbol, limit=limit)
            analysis = analyze_financials(sec_result["annual_rows"])
            score = float(analysis["total_score"])
            is_suitable = score >= SUITABLE_THRESHOLD
            cache_info = sec_result.get("cache") or {}
            if cache_info.get("used"):
                cache_hit_count += 1

            row.update(
                {
                    "name": sec_result.get("entity_name") or holding_name,
                    "companyScore": score,
                    "companyVerdict": "적합" if is_suitable else "부적합",
                    "analysisSuccess": True,
                    "cache": cache_info,
                }
            )

            success_count += 1
            score_sum += score
            weighted_score_sum += score * holding_weight
            weight_sum += holding_weight
        except (SECClientError, AnalysisError) as exc:
            row["failureReason"] = str(exc)
        except Exception as exc:  # pragma: no cover - defensive boundary for one holding
            row["failureReason"] = f"Unexpected analysis error: {exc}"

        holding_rows.append(row)

    simple_average_score = score_sum / success_count if success_count else None
    weighted_average_score = weighted_score_sum / weight_sum if weight_sum else simple_average_score
    is_suitable = weighted_average_score is not None and weighted_average_score >= SUITABLE_THRESHOLD
    verdict = "적합" if is_suitable else "부적합"

    return {
        "etfTicker": symbol,
        "holdingRows": holding_rows,
        "summary": {
            "etfTicker": symbol,
            "successfulCount": success_count,
            "cacheHitCount": cache_hit_count,
            "simpleAverageScore": simple_average_score,
            "weightedAverageScore": weighted_average_score,
            "verdict": verdict,
        },
        "totalScore": weighted_average_score,
        "maxScore": 7.0,
        "isSuitable": is_suitable,
        "verdict": verdict,
    }
