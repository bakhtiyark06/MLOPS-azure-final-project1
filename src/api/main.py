# Author: Member C — FastAPI inference service
# Purpose: Expose /health and /predict for the outage model

"""FastAPI application for website outage prediction."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request

from src.api.config import ApiSettings, get_api_settings
from src.api.inference import features_from_request, load_model, predict_outage
from src.api.schemas import DriftActivityStatus, HealthResponse, PredictRequest, PredictResponse
from src.data.preprocess import get_feature_columns
from src.api.local_dashboard import register_local_dashboard
from src.api.architecture_page import register_architecture_pages
from src.api.swagger_ui import OPENAPI_DESCRIPTION, OPENAPI_TAGS, register_custom_docs
from src.api.drift_service import try_update_drift_after_activity
from src.monitoring.observations import append_observation
from src.monitoring.telemetry import instrument_fastapi, setup_telemetry

logger = logging.getLogger(__name__)

_state: dict[str, Any] = {"model": None, "load_error": None}


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    settings = settings or get_api_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        setup_telemetry(service_name=settings.app_name)
        try:
            _state["model"] = load_model(settings.model_path)
            _state["load_error"] = None
            logger.info("Loaded model from %s", settings.model_path)
        except FileNotFoundError as exc:
            _state["model"] = None
            _state["load_error"] = str(exc)
            logger.warning("Model not loaded: %s", exc)
        yield
        _state["model"] = None

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=OPENAPI_DESCRIPTION,
        contact={"name": "MLOps Team", "url": "https://github.com/YOUR_ORG/MLOPS-azure-final-project1"},
        license_info={"name": "Course Project"},
        openapi_tags=OPENAPI_TAGS,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    instrument_fastapi(app)

    @app.middleware("http")
    async def log_request_metrics(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="Check service status",
        description="Returns API health and whether the outage prediction model is loaded.",
    )
    def health() -> HealthResponse:
        model_loaded = _state.get("model") is not None
        return HealthResponse(
            status="ok" if model_loaded else "degraded",
            model_loaded=model_loaded,
            feature_count=len(get_feature_columns()),
        )

    @app.post(
        "/predict",
        response_model=PredictResponse,
        tags=["Prediction"],
        summary="Predict outage risk from infrastructure metrics",
        description=(
            "Accepts raw monitoring metrics (response time, error rate, CPU, memory, etc.) "
            "and returns outage probability from the trained model."
        ),
    )
    def predict(payload: PredictRequest) -> PredictResponse:
        model = _state.get("model")
        if model is None:
            detail = _state.get("load_error") or "Model artifact is not available"
            raise HTTPException(status_code=503, detail=detail)

        features = features_from_request(payload.model_dump())
        result = predict_outage(model, features)
        logger.info(
            "prediction outage_probability=%.4f outage_predicted=%s",
            result.get("outage_probability", 0.0),
            result.get("outage_predicted"),
        )

        # Demo-triggered drift: append observation and refresh report (non-blocking).
        # Production systems usually schedule/batch drift checks instead.
        drift_status: DriftActivityStatus | None = None
        try:
            feature_dict = payload.model_dump()
            append_observation(
                feature_dict,
                outage_predicted=bool(result["outage_predicted"]),
                outage_probability=float(result["outage_probability"]),
                source="predict",
            )
            drift_status = DriftActivityStatus(**try_update_drift_after_activity())
        except Exception as exc:
            logger.warning("Drift hook after predict failed (prediction still returned): %s", exc)

        return PredictResponse(**result, drift=drift_status)

    def reload_model() -> None:
        try:
            _state["model"] = load_model(settings.model_path)
            _state["load_error"] = None
            logger.info("Reloaded model from %s", settings.model_path)
        except FileNotFoundError as exc:
            _state["model"] = None
            _state["load_error"] = str(exc)
            logger.warning("Model reload failed: %s", exc)

    register_local_dashboard(
        app,
        get_state=lambda: _state,
        reload_model=reload_model,
        settings=settings,
    )
    register_architecture_pages(app)
    register_custom_docs(app)
    return app


app = create_app()
