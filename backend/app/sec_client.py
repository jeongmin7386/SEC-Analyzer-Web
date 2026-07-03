"""SEC EDGAR client and companyfacts annual data extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import gzip
import json
import os
import time
from typing import Any, Iterable
import urllib.error
import urllib.parse
import urllib.request
import zlib

try:
    import requests as _requests

    if not hasattr(_requests, "Session"):
        raise ImportError("requests.Session is unavailable")
    requests = _requests
except (ImportError, AttributeError):
    requests = None


SEC_WWW_BASE_URL = "https://www.sec.gov"
SEC_DATA_BASE_URL = "https://data.sec.gov"
DEFAULT_USER_AGENT = "Personal project stock analyzer contact@example.com"
SEC_USER_AGENT_ENV = "SEC_USER_AGENT"
SEC_USER_AGENT_REQUIRED_MESSAGE = "SEC_USER_AGENT 환경변수가 설정되지 않았습니다"

ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}

TAG_CANDIDATES = {
    "Revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
    ),
    "NetIncomeLoss": ("NetIncomeLoss",),
    "AssetsCurrent": ("AssetsCurrent",),
    "Assets": ("Assets",),
    "LiabilitiesCurrent": ("LiabilitiesCurrent",),
    "Liabilities": ("Liabilities",),
    "StockholdersEquity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ),
    "WeightedAverageNumberOfSharesOutstanding": (
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        "CommonStocksIncludingAdditionalPaidInCapital",
    ),
    "EarningsPerShareBasic": (
        "EarningsPerShareBasic",
        "EarningsPerShareDiluted",
    ),
}

UNIT_PRIORITY = {
    "Revenue": ("USD",),
    "NetIncomeLoss": ("USD",),
    "AssetsCurrent": ("USD",),
    "Assets": ("USD",),
    "LiabilitiesCurrent": ("USD",),
    "Liabilities": ("USD",),
    "StockholdersEquity": ("USD",),
    "WeightedAverageNumberOfSharesOutstanding": ("shares", "USD"),
    "EarningsPerShareBasic": ("USD/shares",),
}


class SECClientError(RuntimeError):
    """Raised when SEC EDGAR data cannot be fetched or normalized."""


class SECConfigurationError(SECClientError):
    """Raised when required SEC client configuration is missing."""


class _UrllibResponse:
    def __init__(self, status_code: int, body: bytes, headers: Any | None = None) -> None:
        self.status_code = status_code
        self._body = body
        self.headers = {str(key).lower(): str(value) for key, value in dict(headers or {}).items()}

    def json(self) -> Any:
        body = self._decode_body()
        return json.loads(body.decode("utf-8"))

    def _decode_body(self) -> bytes:
        encoding = self.headers.get("content-encoding", "").lower()
        if "gzip" in encoding:
            return gzip.decompress(self._body)
        if "deflate" in encoding:
            return zlib.decompress(self._body)
        return self._body


class _UrllibSession:
    def __init__(self) -> None:
        self.headers: dict[str, str] = {}

    def get(self, url: str, timeout: int, headers: dict[str, str] | None = None) -> _UrllibResponse:
        request_headers = {**self.headers, **(headers or {})}
        request = urllib.request.Request(url, headers=request_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return _UrllibResponse(response.status, response.read(), response.headers)
        except urllib.error.HTTPError as exc:
            return _UrllibResponse(exc.code, exc.read(), exc.headers)


@dataclass
class SECClient:
    user_agent: str = DEFAULT_USER_AGENT
    timeout: int = 30
    min_interval_seconds: float = 0.2
    session: Any = field(default_factory=lambda: requests.Session() if requests else _UrllibSession())
    _last_request_at: float = field(default=0.0, init=False)
    _ticker_map: dict[str, dict[str, Any]] | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        configured_user_agent = os.getenv(SEC_USER_AGENT_ENV, "").strip()
        if configured_user_agent:
            self.user_agent = configured_user_agent

    def get_company_profile(self, ticker: str) -> dict[str, Any]:
        ticker_map = self.get_ticker_map()
        profile = ticker_map.get(ticker.upper())
        if profile is None:
            raise SECClientError(f"{ticker.upper()} 티커를 SEC company_tickers.json에서 찾을 수 없습니다.")
        return profile

    def get_ticker_map(self) -> dict[str, dict[str, Any]]:
        if self._ticker_map is not None:
            return self._ticker_map

        payload = self._get_json(f"{SEC_WWW_BASE_URL}/files/company_tickers.json")
        if not isinstance(payload, dict):
            raise SECClientError("SEC company_tickers.json 응답 형식이 예상과 다릅니다.")

        ticker_map: dict[str, dict[str, Any]] = {}
        for item in payload.values():
            if not isinstance(item, dict):
                continue

            ticker = str(item.get("ticker", "")).strip().upper()
            cik = item.get("cik_str")
            if not ticker or cik is None:
                continue

            ticker_map[ticker] = {
                "ticker": ticker,
                "cik": str(cik).zfill(10),
                "title": str(item.get("title") or "").strip(),
            }

        if not ticker_map:
            raise SECClientError("SEC 티커/CIK 매핑 데이터를 읽을 수 없습니다.")

        self._ticker_map = ticker_map
        return ticker_map

    def get_companyfacts(self, cik: str) -> dict[str, Any]:
        cik = str(cik).zfill(10)
        payload = self._get_json(f"{SEC_DATA_BASE_URL}/api/xbrl/companyfacts/CIK{cik}.json")
        if not isinstance(payload, dict):
            raise SECClientError("SEC companyfacts 응답 형식이 예상과 다릅니다.")
        return payload

    def get_submissions(self, cik: str) -> dict[str, Any]:
        cik = str(cik).zfill(10)
        payload = self._get_json(f"{SEC_DATA_BASE_URL}/submissions/CIK{cik}.json")
        if not isinstance(payload, dict):
            raise SECClientError("SEC submissions 응답 형식이 예상과 다릅니다.")
        return payload

    def fetch_annual_financials(self, ticker: str, limit: int = 10) -> dict[str, Any]:
        profile = self.get_company_profile(ticker)
        companyfacts = self.get_companyfacts(profile["cik"])
        annual_rows, selected_tags = extract_annual_financial_rows(companyfacts, limit=limit)

        if not annual_rows:
            raise SECClientError(f"{ticker.upper()}에서 계산 가능한 SEC 연간 재무 데이터를 찾을 수 없습니다.")

        return {
            "profile": profile,
            "entity_name": companyfacts.get("entityName") or profile.get("title") or ticker.upper(),
            "annual_rows": annual_rows,
            "selected_tags": selected_tags,
        }

    def _get_json(self, url: str) -> Any:
        self._respect_rate_limit()
        headers = self._sec_headers(url)

        try:
            response = self.session.get(url, timeout=self.timeout, headers=headers)
            if response.status_code >= 400:
                raise SECClientError(f"SEC API HTTP 오류 {response.status_code}: {url}")
            return response.json()
        except _request_exception_types() as exc:
            raise SECClientError(f"SEC API 요청에 실패했습니다: {exc}") from exc
        except ValueError as exc:
            raise SECClientError("SEC API 응답을 JSON으로 해석할 수 없습니다.") from exc

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()

    def _sec_headers(self, url: str) -> dict[str, str]:
        user_agent = self._configured_user_agent()
        host = urllib.parse.urlparse(url).hostname or "www.sec.gov"
        return {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": host,
            "Accept": "application/json",
        }

    def _configured_user_agent(self) -> str:
        user_agent = os.getenv(SEC_USER_AGENT_ENV, "").strip()
        if not user_agent:
            raise SECConfigurationError(SEC_USER_AGENT_REQUIRED_MESSAGE)
        return user_agent


def extract_annual_financial_rows(
    companyfacts: dict[str, Any],
    limit: int = 10,
) -> tuple[list[dict[str, Any]], dict[str, str | None]]:
    facts = companyfacts.get("facts", {}).get("us-gaap", {})
    if not isinstance(facts, dict):
        raise SECClientError("SEC companyfacts에 us-gaap 데이터가 없습니다.")

    value_sets: dict[str, dict[int, dict[str, Any]]] = {}
    selected_tags: dict[str, str | None] = {}

    for metric_key, tags in TAG_CANDIDATES.items():
        values, tag = _extract_values_by_year(
            facts=facts,
            tags=tags,
            preferred_units=UNIT_PRIORITY.get(metric_key, ()),
        )
        value_sets[metric_key] = values
        selected_tags[metric_key] = tag

    years = sorted(
        {year for values in value_sets.values() for year in values},
        reverse=True,
    )[:limit]

    rows: list[dict[str, Any]] = []
    for year in sorted(years):
        rows.append(
            {
                "fiscal_year": year,
                "date": _date_for_year(value_sets, year),
                "Revenue": _value_for_year(value_sets["Revenue"], year),
                "NetIncomeLoss": _value_for_year(value_sets["NetIncomeLoss"], year),
                "Assets": _value_for_year(value_sets["Assets"], year),
                "Liabilities": _value_for_year(value_sets["Liabilities"], year),
                "StockholdersEquity": _value_for_year(value_sets["StockholdersEquity"], year),
                "AssetsCurrent": _value_for_year(value_sets["AssetsCurrent"], year),
                "LiabilitiesCurrent": _value_for_year(value_sets["LiabilitiesCurrent"], year),
                "WeightedAverageNumberOfSharesOutstanding": _value_for_year(
                    value_sets["WeightedAverageNumberOfSharesOutstanding"],
                    year,
                ),
                "EarningsPerShareBasic": _value_for_year(
                    value_sets["EarningsPerShareBasic"],
                    year,
                ),
            }
        )

    return rows, selected_tags


def _extract_values_by_year(
    facts: dict[str, Any],
    tags: Iterable[str],
    preferred_units: Iterable[str],
) -> tuple[dict[int, dict[str, Any]], str | None]:
    values: dict[int, dict[str, Any]] = {}
    used_tags: list[str] = []

    for tag in tags:
        concept = facts.get(tag)
        if not isinstance(concept, dict):
            continue

        units = concept.get("units")
        if not isinstance(units, dict):
            continue

        tag_values: dict[int, dict[str, Any]] = {}
        for unit in _ordered_units(units, preferred_units):
            fact_rows = units.get(unit)
            if not isinstance(fact_rows, list):
                continue

            for fact in fact_rows:
                normalized = _normalize_fact(fact, tag=tag, unit=unit)
                if normalized is None:
                    continue

                year = normalized["fiscal_year"]
                current = tag_values.get(year)
                if current is None or _fact_sort_key(normalized) > _fact_sort_key(current):
                    tag_values[year] = normalized

        added = False
        for year, normalized in tag_values.items():
            if year not in values:
                values[year] = normalized
                added = True

        if added:
            used_tags.append(tag)

    return values, ", ".join(used_tags) if used_tags else None


def _normalize_fact(fact: Any, tag: str, unit: str) -> dict[str, Any] | None:
    if not isinstance(fact, dict) or not _is_annual_fact(fact):
        return None

    year = _to_int(fact.get("fy")) or _year_from_date(fact.get("end"))
    value = _to_float(fact.get("val"))
    if year is None or value is None:
        return None

    return {
        "fiscal_year": year,
        "value": value,
        "filed": str(fact.get("filed") or ""),
        "end": str(fact.get("end") or ""),
        "form": str(fact.get("form") or ""),
        "tag": tag,
        "unit": unit,
    }


def _is_annual_fact(fact: dict[str, Any]) -> bool:
    form = str(fact.get("form") or "").upper()
    if form not in ANNUAL_FORMS:
        return False

    if str(fact.get("fp") or "").upper() == "FY":
        return True

    start = _parse_date(fact.get("start"))
    end = _parse_date(fact.get("end"))
    if start is None or end is None:
        return True

    duration_days = (end - start).days
    return 270 <= duration_days <= 460


def _ordered_units(units: dict[str, Any], preferred_units: Iterable[str]) -> list[str]:
    preferred = [unit for unit in preferred_units if unit in units]
    remaining = [unit for unit in units if unit not in preferred]
    return preferred + remaining


def _fact_sort_key(fact: dict[str, Any]) -> tuple[str, str]:
    return (str(fact.get("filed") or ""), str(fact.get("end") or ""))


def _value_for_year(values: dict[int, dict[str, Any]], year: int) -> float | None:
    row = values.get(year)
    if row is None:
        return None
    return row["value"]


def _date_for_year(value_sets: dict[str, dict[int, dict[str, Any]]], year: int) -> str | None:
    for key in (
        "Revenue",
        "NetIncomeLoss",
        "EarningsPerShareBasic",
        "WeightedAverageNumberOfSharesOutstanding",
    ):
        row = value_sets.get(key, {}).get(year)
        if row and row.get("end"):
            return str(row["end"])
    return None


def _to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _to_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _year_from_date(value: Any) -> int | None:
    if isinstance(value, str) and len(value) >= 4:
        return _to_int(value[:4])
    return None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _request_exception_types() -> tuple[type[BaseException], ...]:
    if requests is not None:
        return (requests.RequestException,)
    return (urllib.error.URLError, TimeoutError, OSError)
