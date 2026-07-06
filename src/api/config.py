# Author: TODO - Team Member Name
# Responsibility: TODO - API Configuration
# Last Reviewed: TODO

"""API configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from src.utils.config import get_project_root


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Website Outage Prediction API"
    app_version: str = "1.0.0"
    model_path: Path = get_project_root() / "models" / "outage_model.joblib"


def get_api_settings() -> ApiSettings:
    return ApiSettings()
