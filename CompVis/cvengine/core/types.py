"""Shared type definitions used across the entire framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class TaskType(str, Enum):
    CLASSIFICATION = "classification"
    DETECTION = "detection"
    SEGMENTATION = "segmentation"
    OCR = "ocr"


@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float = 1.0
    class_id: int = 0
    class_name: str = ""

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def iou(self, other: BoundingBox) -> float:
        ix1, iy1 = max(self.x1, other.x1), max(self.y1, other.y1)
        ix2, iy2 = min(self.x2, other.x2), min(self.y2, other.y2)
        inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2,
            "confidence": self.confidence,
            "class_id": self.class_id,
            "class_name": self.class_name,
        }


@dataclass
class Prediction:
    """Unified prediction container for all CV tasks."""

    task: TaskType
    # Classification
    class_id: int | None = None
    class_name: str | None = None
    confidence: float | None = None
    top_k: list[dict[str, Any]] | None = None
    # Detection
    boxes: list[BoundingBox] | None = None
    # Segmentation
    mask: np.ndarray | None = None
    class_map: dict[int, str] | None = None
    # OCR
    text: str | None = None
    text_regions: list[dict[str, Any]] | None = None
    # Metadata
    inference_time_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"task": self.task.value, "inference_time_ms": self.inference_time_ms}
        if self.task == TaskType.CLASSIFICATION:
            d.update(class_id=self.class_id, class_name=self.class_name,
                     confidence=self.confidence, top_k=self.top_k)
        elif self.task == TaskType.DETECTION:
            d["boxes"] = [b.to_dict() for b in (self.boxes or [])]
        elif self.task == TaskType.SEGMENTATION:
            d["mask_shape"] = list(self.mask.shape) if self.mask is not None else None
            d["class_map"] = self.class_map
        elif self.task == TaskType.OCR:
            d.update(text=self.text, text_regions=self.text_regions)
        d["metadata"] = self.metadata
        return d


@dataclass
class BatchPrediction:
    predictions: list[Prediction]
    total_time_ms: float = 0.0

    def __len__(self) -> int:
        return len(self.predictions)

    def __getitem__(self, idx: int) -> Prediction:
        return self.predictions[idx]

    def __iter__(self):
        return iter(self.predictions)
