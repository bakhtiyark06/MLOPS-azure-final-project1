"""Request and response schemas for the prediction API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.data.preprocess import get_feature_columns

_PREDICT_EXAMPLE = {
    "response_time_ms": 850.0,
    "status_code": 500.0,
    "error_rate": 0.12,
    "latency_p95_ms": 1200.0,
    "request_count": 4200.0,
    "cpu_usage_percent": 78.0,
    "memory_usage_percent": 81.0,
}


class HealthResponse(BaseModel):
    status: str = Field(description="Service status: ok when model is loaded, degraded otherwise.")
    model_loaded: bool = Field(description="Whether the outage model artifact is loaded in memory.")
    feature_count: int = Field(description="Number of features expected by the model.")


class PredictRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [_PREDICT_EXAMPLE]},
    )

    response_time_ms: float = Field(..., ge=0, description="Average HTTP response time in milliseconds.")
    status_code: float = Field(..., ge=100, le=599, description="HTTP status code (e.g. 200, 500).")
    error_rate: float = Field(..., ge=0, le=1, description="Fraction of failed requests (0.0–1.0).")
    latency_p95_ms: float = Field(..., ge=0, description="95th percentile latency in milliseconds.")
    request_count: float = Field(..., ge=0, description="Number of requests in the observation window.")
    cpu_usage_percent: float = Field(..., ge=0, le=100, description="CPU utilization percentage.")
    memory_usage_percent: float = Field(..., ge=0, le=100, description="Memory utilization percentage.")


class DriftActivityStatus(BaseModel):
    updated: bool = Field(description="Whether a drift report was regenerated.")
    insufficient_data: bool = Field(
        default=False,
        description="True when fewer than min observations exist for drift analysis.",
    )
    dataset_drift: bool | None = Field(
        default=None,
        description="Whether dataset-level drift was detected (when analysis ran).",
    )
    drift_score: float | None = Field(
        default=None,
        description="Fraction of features that drifted (0.0–1.0).",
    )
    drifted_columns: list[str] = Field(
        default_factory=list,
        description="Feature names flagged as drifted.",
    )
    message: str = Field(default="", description="Human-readable drift update status.")
    observation_count: int | None = Field(
        default=None,
        description="Number of demo production observations logged so far.",
    )


class PredictResponse(BaseModel):
    outage_predicted: bool = Field(description="True if the model predicts an imminent outage.")
    outage_probability: float = Field(
        ...,
        ge=0,
        le=1,
        description="Probability of outage (0.0 = safe, 1.0 = certain).",
    )
    drift: DriftActivityStatus | None = Field(
        default=None,
        description="Demo-triggered drift status after this prediction (non-blocking).",
    )


class UrlCheckRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"url": "https://example.com"}]},
    )

    url: str = Field(..., min_length=1, description="Public http or https URL to probe.")


class OpenRouterReportResponse(BaseModel):
    exists: bool = Field(description="Whether the markdown report file exists.")
    content: str | None = Field(default=None, description="Full markdown report body.")
    report_path: str | None = Field(default=None, description="Absolute or project-relative report path.")
    generated_at: str | None = Field(default=None, description="ISO UTC timestamp when report was generated.")
    source: str | None = Field(
        default=None,
        description="Generation source: openrouter or local_fallback.",
    )
    openrouter_api_used: bool | None = Field(
        default=None,
        description="True when the OpenRouter API was used successfully.",
    )
    preview: str | None = Field(default=None, description="Short plain-text preview of the report.")
    message: str = Field(default="", description="Human-readable status message.")


class OpenRouterRunResponse(BaseModel):
    success: bool = Field(description="Whether report generation completed.")
    report_path: str = Field(description="Path to the written markdown report.")
    generated_at: str = Field(description="ISO UTC timestamp.")
    source: str = Field(description="openrouter or local_fallback.")
    openrouter_api_used: bool = Field(description="True when OpenRouter API was used.")
    preview: str = Field(description="Short preview of generated content.")
    message: str = Field(description="Human-readable result message.")


class UrlMetricsResponse(BaseModel):
    response_time_ms: float = Field(..., ge=0, description="Average response time from live probes.")
    status_code: float = Field(..., ge=0, le=599, description="Last observed HTTP status code.")
    error_rate: float = Field(..., ge=0, le=1, description="Fraction of failed probe requests.")
    latency_p95_ms: float = Field(..., ge=0, description="95th percentile latency across probes.")
    request_count: float = Field(..., ge=0, description="Number of probe requests performed.")
    cpu_usage_percent: float = Field(..., ge=0, le=100, description="Estimated CPU usage (proxy metric).")
    memory_usage_percent: float = Field(..., ge=0, le=100, description="Estimated memory usage (proxy metric).")
    note: str = Field(description="Human-readable summary of the probe result.")
    outage_predicted: bool | None = Field(
        default=None,
        description="Model outage prediction from probed metrics (when model is loaded).",
    )
    outage_probability: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Model confidence from probed metrics (when model is loaded).",
    )
    drift: DriftActivityStatus | None = Field(
        default=None,
        description="Demo-triggered drift status after this URL check (non-blocking).",
    )
