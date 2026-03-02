"""FastAPI backend for CVEngine — drop-in REST API for any CV task.

Run:
    uvicorn api.main:app --reload --port 8000

Endpoints:
    POST /predict         — upload image, get predictions
    POST /predict/batch   — upload multiple images
    POST /switch-model    — hot-swap the active model
    GET  /health          — health check
    GET  /models          — list registered models
"""

from __future__ import annotations

import io
import time
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.schemas import HealthResponse, ModelSwitchRequest, PredictionResponse
from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.inference.pipeline import InferencePipeline
from cvengine.utils.io import load_image

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_pipeline: InferencePipeline | None = None
_config: Config = Config()


def _init_pipeline(config: Config | None = None) -> InferencePipeline:
    global _pipeline, _config
    _config = config or Config()
    _pipeline = InferencePipeline.from_config(config_dict=_config.to_dict())
    return _pipeline


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_pipeline()
    yield


app = FastAPI(title="CVEngine API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        model=_config.get("model.name", ""),
        task=_config.get("task", ""),
        device=str(_pipeline.model.device) if _pipeline else "none",
    )


@app.get("/models")
async def list_models():
    import cvengine.models  # noqa: F401 — ensure registered
    return {"models": ModelRegistry.list_keys()}


@app.post("/predict", response_model=PredictionResponse)
async def predict(file: UploadFile = File(...)):
    assert _pipeline is not None
    contents = await file.read()
    image = load_image(contents, color="rgb")
    pred = _pipeline(image)
    return PredictionResponse(**pred.to_dict())


@app.post("/predict/batch")
async def predict_batch(files: list[UploadFile] = File(...)):
    assert _pipeline is not None
    images = []
    for f in files:
        data = await f.read()
        images.append(load_image(data, color="rgb"))
    preds = _pipeline.predict_batch(images)
    return [PredictionResponse(**p.to_dict()) for p in preds]


@app.post("/switch-model")
async def switch_model(req: ModelSwitchRequest):
    new_config = _config.merge({"model": {"name": req.model_name}, **req.config_overrides})
    _init_pipeline(new_config)
    return {"status": "ok", "model": req.model_name}
