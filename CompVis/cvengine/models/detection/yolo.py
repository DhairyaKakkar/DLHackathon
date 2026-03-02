"""YOLOv8 wrapper via the ultralytics library."""

from __future__ import annotations

import os
import time
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from cvengine.core.base import BaseModel
from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import BoundingBox, Prediction, TaskType

# MPS does not support torchvision::nms — force CPU fallback
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")


class _Placeholder(nn.Module):
    """Dummy module so BaseModel.save/load don't break.
    We never route inference through this — YOLO handles it internally."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x


@ModelRegistry.register("yolov8n", task="detection", family="yolo")
@ModelRegistry.register("yolov8s", task="detection", family="yolo")
@ModelRegistry.register("yolov8m", task="detection", family="yolo")
@ModelRegistry.register("yolov8l", task="detection", family="yolo")
@ModelRegistry.register("yolov8x", task="detection", family="yolo")
class YOLOv8Wrapper(BaseModel):

    def __init__(self, config: Config):
        # Override BaseModel.__init__ completely to avoid calling .eval()
        # on the YOLO object (ultralytics hijacks .train() / .eval()).
        self.config = config
        self.device = self._resolve_device(config.get("inference.device", "auto"))
        self._conf = config.get("inference.confidence_threshold", 0.5)
        self._iou = config.get("inference.nms_threshold", 0.45)

        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError("Install ultralytics: pip install ultralytics")

        name = config.get("model.name", "yolov8n")
        weights = config.get("model.weights")
        model_path = weights if weights else f"{name}.pt"

        self._yolo = YOLO(model_path, task="detect")
        # Placeholder so BaseModel helpers like parameter_count() don't crash
        self.model = _Placeholder()

    @property
    def task_type(self) -> TaskType:
        return TaskType.DETECTION

    def build_model(self, config: Config) -> nn.Module:
        # Not used — __init__ is overridden
        return _Placeholder()

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        return torch.empty(0)

    @torch.inference_mode()
    def predict(self, image: np.ndarray) -> Prediction:
        t0 = time.perf_counter()
        results = self._yolo.predict(
            image,
            conf=self._conf,
            iou=self._iou,
            verbose=False,
            save=False,
            device=str(self.device),
        )
        boxes = []
        for r in results:
            for box in r.boxes:
                xyxy = box.xyxy[0].tolist()
                boxes.append(BoundingBox(
                    x1=xyxy[0], y1=xyxy[1], x2=xyxy[2], y2=xyxy[3],
                    confidence=float(box.conf[0]),
                    class_id=int(box.cls[0]),
                    class_name=r.names[int(box.cls[0])],
                ))
        elapsed = (time.perf_counter() - t0) * 1000
        return Prediction(task=TaskType.DETECTION, boxes=boxes, inference_time_ms=elapsed)

    def postprocess(self, output: Any, original_shape: tuple[int, ...]) -> Prediction:
        return Prediction(task=TaskType.DETECTION, boxes=[])

    def parameter_count(self) -> dict[str, int]:
        try:
            p = sum(x.numel() for x in self._yolo.model.parameters())
            return {"total": p, "trainable": p, "frozen": 0}
        except Exception:
            return {"total": 0, "trainable": 0, "frozen": 0}

    def save(self, path) -> None:
        pass  # YOLO manages its own weights

    def load(self, path) -> None:
        from ultralytics import YOLO
        self._yolo = YOLO(str(path), task="detect")
