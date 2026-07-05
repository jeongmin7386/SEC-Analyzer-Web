"""API request schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class StockAnalysisRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16)
    includePrice: bool = True
    pricePeriod: str = "1y"


class ETFAnalysisRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=16)
    manualHoldings: str | None = None
