"""Request and response schemas for the prediction API."""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.data.preprocess import get_feature_columns


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    feature_count: int


class PredictRequest(BaseModel):
    response_time_ms: float = Field(..., ge=0)
    status_code: float = Field(..., ge=100, le=599)
    error_rate: float = Field(..., ge=0, le=1)
    latency_p95_ms: float = Field(..., ge=0)
    request_count: float = Field(..., ge=0)
    cpu_usage_percent: float = Field(..., ge=0, le=100)
    memory_usage_percent: float = Field(..., ge=0, le=100)


class PredictResponse(BaseModel):
    outage_predicted: bool
    outage_probability: float = Field(..., ge=0, le=1)


class UrlCheckRequest(BaseModel):
    url: str = Field(..., min_length=1)


class UrlMetricsResponse(BaseModel):
    response_time_ms: float = Field(..., ge=0)
    status_code: float = Field(..., ge=0, le=599)
    error_rate: float = Field(..., ge=0, le=1)
    latency_p95_ms: float = Field(..., ge=0)
    request_count: float = Field(..., ge=0)
    cpu_usage_percent: float = Field(..., ge=0, le=100)
    memory_usage_percent: float = Field(..., ge=0, le=100)
    note: str
