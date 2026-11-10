"""Pydantic response contracts shared by inference and history."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator


class PredictionResponse(BaseModel):
    record_id: int
    filename: str
    predicted_class: Literal["REAL", "FAKE"]
    real_probability: float = Field(ge=0, le=1)
    fake_probability: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1, description="Selected-class model score, not calibrated certainty.")
    threshold: float = Field(ge=0, le=1)
    processing_time_ms: float = Field(ge=0)
    gradcam_image: str | None = Field(None, description="Legacy alias for gradcam_overlay: raw base64 PNG.")
    gradcam_heatmap: str | None = Field(None, description="Raw base64 PNG of relative class attention.")
    gradcam_overlay: str | None = Field(None, description="Raw base64 PNG overlay, max 1024px longest edge.")
    gradcam_error: str | None = None


class HistoryRecord(BaseModel):
    id: int
    original_filename: str
    predicted_class: Literal["REAL", "FAKE"]
    real_probability: float = Field(ge=0, le=1)
    fake_probability: float = Field(ge=0, le=1)
    confidence_score: float = Field(ge=0, le=1)
    threshold: float | None = Field(None, ge=0, le=1)
    processing_time_ms: float = Field(ge=0)
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        # SQLite CURRENT_TIMESTAMP is UTC even for pre-migration rows.
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class HistoryResponse(BaseModel):
    items: list[HistoryRecord]
    total: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str | None
    tensorflow_version: str
    threshold: float | None
    model_error: str | None = None
