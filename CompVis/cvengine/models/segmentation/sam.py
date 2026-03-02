"""Segment Anything Model (SAM) wrapper for zero-shot segmentation."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from cvengine.core.base import BaseModel
from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import Prediction, TaskType


class _SAMShell(nn.Module):
    """Holds a reference to the SAM predictor so BaseModel machinery works."""

    def __init__(self, predictor: Any):
        super().__init__()
        self.predictor = predictor

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x


@ModelRegistry.register("sam_vit_h", task="segmentation", family="sam")
@ModelRegistry.register("sam_vit_l", task="segmentation", family="sam")
@ModelRegistry.register("sam_vit_b", task="segmentation", family="sam")
class SAMWrapper(BaseModel):
    """Zero-shot segmentation via SAM with point or box prompts.

    Requires: pip install segment-anything
    Download weights from https://github.com/facebookresearch/segment-anything
    """

    @property
    def task_type(self) -> TaskType:
        return TaskType.SEGMENTATION

    def build_model(self, config: Config) -> nn.Module:
        try:
            from segment_anything import SamPredictor, sam_model_registry
        except ImportError:
            raise ImportError("Install segment-anything: pip install segment-anything")

        variant_map = {"sam_vit_h": "vit_h", "sam_vit_l": "vit_l", "sam_vit_b": "vit_b"}
        name = config.get("model.name", "sam_vit_b")
        checkpoint = config.get("model.weights")
        if not checkpoint:
            raise ValueError("SAM requires model.weights pointing to a .pth checkpoint")

        sam = sam_model_registry[variant_map.get(name, "vit_b")](checkpoint=checkpoint)
        sam.to(self.device)
        self._predictor = SamPredictor(sam)
        return _SAMShell(self._predictor)

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        self._predictor.set_image(image)
        return torch.empty(0)

    @torch.inference_mode()
    def predict(self, image: np.ndarray, point_coords: np.ndarray | None = None,
                point_labels: np.ndarray | None = None,
                box: np.ndarray | None = None) -> Prediction:
        t0 = time.perf_counter()
        self._predictor.set_image(image)
        masks, scores, _ = self._predictor.predict(
            point_coords=point_coords, point_labels=point_labels, box=box,
            multimask_output=True,
        )
        best = int(scores.argmax())
        elapsed = (time.perf_counter() - t0) * 1000
        return Prediction(
            task=TaskType.SEGMENTATION,
            mask=masks[best].astype(np.uint8),
            confidence=float(scores[best]),
            inference_time_ms=elapsed,
        )

    def postprocess(self, output: Any, original_shape: tuple[int, ...]) -> Prediction:
        return Prediction(task=TaskType.SEGMENTATION)
