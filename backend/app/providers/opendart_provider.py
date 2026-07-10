"""Korean stock provider backed by OpenDART."""

from __future__ import annotations

from datetime import date
import os
from pathlib import Path
import time
from typing import Any

import requests

from ..cache import JsonFileCache, cache_meta
from ..market_data import MarketDataError, get_stock_price_history
from ..opendart_accounts import normalize_dart_statement
from ..stock_master import get_kr_stock, public_stock, search_kr_stocks


OPENDART_API_URL = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
OPENDART_API_KEY_ENV = "OPENDART_API_KEY"


class OpenDARTError(RuntimeError):
    """Raised when OpenDART data cannot be fetched or normalized."""


class OpenDARTConfigurationError(OpenDARTError):
    """Raised when OpenDART configuration is missing."""


class OpenDARTProvider:
    market = "KR"

    def __init__(
        self,
        api_key: str | None = None,
        session: requests.Session | None = None,
        cache: JsonFileCache | None = None,
        min_interval_seconds: float = 0.25,
    ) -> None:
        self.api_key = (api_key or os.getenv(OPENDART_API_KEY_ENV, "")).strip()
        self.session = session or requests.Session()
        self.cache = cache or JsonFileCache(
            directory=Path(__file__).resolve().parents[2] / "cache" / "opendart",
            ttl_seconds=24 * 60 * 60,
        )
        self.min_interval_seconds = min_interval_seconds
        self._last_request_at = 0.0
        self._last_cache_meta: dict[str, Any] = {}

    def search_stocks(self, query: str) -> list[dict[str, Any]]:
        return search_kr_stocks(query)

    def get_company_profile(self, symbol: str) -> dict[str, Any]:
        stock = get_kr_stock(symbol)
        if stock is None:
            raise OpenDARTError(f"한국 종목 마스터에서 {symbol}을 찾을 수 없습니다.")
        return public_stock(stock)

    def get_financial_statements(self, symbol: str, years: int = 10) -> dict[str, Any]:
        profile = self.get_company_profile(symbol)
        corp_code = profile.get("corpCode")
        if not corp_code:
            raise OpenDARTError(f"{symbol}의 OpenDART corp_code가 없습니다.")

        financials: list[dict[str, Any]] = []
        cache_items: list[dict[str, Any]] = []
        warnings: list[str] = []
        end_year = latest_annual_report_year()

        for fiscal_year in range(end_year, end_year - max(years, 1), -1):
            try:
                statement, cache_info = self._get_preferred_statement(str(corp_code), fiscal_year)
            except OpenDARTNoDataError as exc:
                warnings.append(str(exc))
                continue

            cache_items.append(cache_info)
            normalized = normalize_dart_statement(
                statement["rows"],
                fiscal_year=fiscal_year,
                currency="KRW",
                fs_div=statement["fsDiv"],
            )
            normalized["filedAt"] = statement.get("receiptNo")
            normalized["sourceUrl"] = "https://opendart.fss.or.kr/"
            normalized["metadata"].update(
                {
                    "corpCode": corp_code,
                    "stockCode": profile["symbol"],
                    "fsName": statement["fsName"],
                    "reportName": "사업보고서",
                    "source": "OpenDART fnlttSinglAcntAll",
                }
            )
            financials.append(normalized)

        if not financials:
            raise OpenDARTError(
                f"{profile['companyName']}의 최근 연간 재무제표를 OpenDART에서 찾지 못했습니다."
            )

        return {
            "company": profile,
            "financials": sorted(financials, key=lambda row: row["fiscalYear"]),
            "dataSource": "OPENDART",
            "currency": "KRW",
            "cache": {
                "items": cache_items,
                "used": bool(cache_items) and all(item.get("used") for item in cache_items),
            },
            "warnings": warnings,
        }

    def get_price_history(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        period: str = "1y",
    ) -> list[dict[str, Any]]:
        del start_date, end_date
        stock = get_kr_stock(symbol)
        if stock is None:
            raise OpenDARTError(f"한국 종목 마스터에서 {symbol}을 찾을 수 없습니다.")
        try:
            return get_stock_price_history(stock.get("priceSymbol") or stock["symbol"], period)
        except MarketDataError:
            raise

    def _get_preferred_statement(self, corp_code: str, fiscal_year: int) -> tuple[dict[str, Any], dict[str, Any]]:
        try:
            return self._get_statement(corp_code, fiscal_year, "CFS")
        except OpenDARTNoDataError:
            return self._get_statement(corp_code, fiscal_year, "OFS")

    def _get_statement(self, corp_code: str, fiscal_year: int, fs_div: str) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = self._request_statement(corp_code, fiscal_year, fs_div)
        rows = payload.get("list")
        if not isinstance(rows, list) or not rows:
            raise OpenDARTNoDataError(f"{fiscal_year}년 {fs_div} 재무제표 데이터가 없습니다.")

        fs_name = "연결재무제표" if fs_div == "CFS" else "별도재무제표"
        receipt_no = next((row.get("rcept_no") for row in rows if row.get("rcept_no")), None)
        return {
            "rows": rows,
            "fsDiv": fs_div,
            "fsName": fs_name,
            "receiptNo": receipt_no,
        }, dict(self._last_cache_meta)

    def _request_statement(self, corp_code: str, fiscal_year: int, fs_div: str) -> dict[str, Any]:
        if not self.api_key:
            raise OpenDARTConfigurationError(
                "한국 주식 분석에는 OPENDART_API_KEY 환경변수가 필요합니다."
            )

        cache_key = f"opendart_{corp_code}_{fiscal_year}_{fs_div}"
        cached = self.cache.get(cache_key)
        if cached.hit and cached.payload is not None:
            self._last_cache_meta = cache_meta(
                used=True,
                source="file",
                key=cache_key,
                path=cached.path,
                age_seconds=cached.age_seconds,
                expires_in_seconds=cached.expires_in_seconds,
            )
            return cached.payload

        self._respect_rate_limit()
        params = {
            "crtfc_key": self.api_key,
            "corp_code": corp_code,
            "bsns_year": str(fiscal_year),
            "reprt_code": "11011",
            "fs_div": fs_div,
        }

        try:
            response = self.session.get(OPENDART_API_URL, params=params, timeout=25)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise OpenDARTError("OpenDART 재무제표 요청에 실패했습니다.") from exc
        except ValueError as exc:
            raise OpenDARTError("OpenDART 응답을 JSON으로 해석할 수 없습니다.") from exc

        status = str(payload.get("status") or "")
        if status == "013":
            raise OpenDARTNoDataError(f"{fiscal_year}년 {fs_div} 재무제표 데이터가 없습니다.")
        if status and status != "000":
            message = str(payload.get("message") or "OpenDART 오류")
            raise OpenDARTError(f"OpenDART 오류: {message}")

        cache_path = self.cache.set(cache_key, payload)
        self._last_cache_meta = cache_meta(
            used=False,
            source="opendart",
            key=cache_key,
            path=cache_path,
        )
        return payload

    def _respect_rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()


class OpenDARTNoDataError(OpenDARTError):
    """Raised for missing annual statement data."""


def latest_annual_report_year() -> int:
    today = date.today()
    if today.month < 4:
        return today.year - 2
    return today.year - 1
