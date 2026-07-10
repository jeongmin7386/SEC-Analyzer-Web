"""API request schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StockAnalysisRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16)
    includePrice: bool = True
    pricePeriod: str = "1y"


class ETFAnalysisRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16)
    manualHoldings: str | None = None


class UnifiedStockAnalysisRequest(BaseModel):
    market: Literal["AUTO", "KR", "US"] = "AUTO"
    symbol: str = Field(..., min_length=1, max_length=64)
    presetId: str = "default"
    years: int = Field(default=10, ge=1, le=20)
    includePrice: bool = True
    pricePeriod: str = "1y"
