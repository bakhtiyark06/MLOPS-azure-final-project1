# Author: Member C — FastAPI inference service
# Purpose: Expose /health and /predict for the outage model

"""FastAPI application for website outage prediction."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException

from src.api.config import ApiSettings, get_api_settings
from src.api.inference import features_from_request, load_model, predict_outage
from src.api.schemas import HealthResponse, PredictRequest, PredictResponse
from src.data.preprocess import get_feature_columns

logger = logging.getLogger(__name__)

_state: dict[str, Any] = {"model": None, "load_error": None}


def create_app(settings: ApiSettings | None = None) -> FastAPI:
    settings = settings or get_api_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
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
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        model_loaded = _state.get("model") is not None
        return HealthResponse(
            status="ok" if model_loaded else "degraded",
            model_loaded=model_loaded,
            feature_count=len(get_feature_columns()),
        )

    @app.post("/predict", response_model=PredictResponse)
    def predict(payload: PredictRequest) -> PredictResponse:
        model = _state.get("model")
        if model is None:
            detail = _state.get("load_error") or "Model artifact is not available"
            raise HTTPException(status_code=503, detail=detail)

        features = features_from_request(payload.model_dump())
        result = predict_outage(model, features)
        return PredictResponse(**result)

    return app


app = create_app()
