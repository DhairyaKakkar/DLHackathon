"""Pydantic schemas for the FastAPI endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PredictionResponse(BaseModel):
    task: str
    class_id: int | None = None
    class_name: str | None = None
    confidence: float | None = None
    top_k: list[dict] | None = None
    boxes: list[dict] | None = None
    mask_shape: list[int] | None = None
    text: str | None = None
    text_regions: list[dict] | None = None
    inference_time_ms: float = 0.0


class HealthResponse(BaseModel):
    status: str = "ok"
    model: str = ""
    task: str = ""
    device: str = ""


class ModelSwitchRequest(BaseModel):
    model_name: str = Field(..., description="Registered model name, e.g. 'yolov8n'")
    config_overrides: dict = Field(default_factory=dict)
