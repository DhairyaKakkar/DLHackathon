"""Abstract base class that every model wrapper must implement."""

from __future__ import annotations

import abc
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from cvengine.core.config import Config
from cvengine.core.types import Prediction, TaskType


class BaseModel(abc.ABC):
    """Contract for all CV model wrappers in the framework.

    Subclasses must implement:
        build_model  -- return a torch.nn.Module
        preprocess   -- numpy image -> model-ready tensor
        postprocess  -- raw model output -> Prediction
    """

    def __init__(self, config: Config):
        self.config = config
        self.device = self._resolve_device(config.get("inference.device", "auto"))
        self.model: nn.Module = self.build_model(config)
        self.model.to(self.device)
        self.model.eval()

    # --- abstract interface ---------------------------------------------------

    @abc.abstractmethod
    def build_model(self, config: Config) -> nn.Module:
        """Construct or load the underlying torch model."""

    @abc.abstractmethod
    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        """Convert a BGR/RGB numpy image to a batched tensor."""

    @abc.abstractmethod
    def postprocess(self, output: Any, original_shape: tuple[int, ...]) -> Prediction:
        """Convert raw model output into a structured Prediction."""

    @property
    @abc.abstractmethod
    def task_type(self) -> TaskType:
        """Return the task this model solves."""

    # --- concrete helpers -----------------------------------------------------

    @torch.inference_mode()
    def predict(self, image: np.ndarray) -> Prediction:
        t0 = time.perf_counter()
        tensor = self.preprocess(image).to(self.device)
        output = self.model(tensor)
        pred = self.postprocess(output, image.shape[:2])
        pred.inference_time_ms = (time.perf_counter() - t0) * 1000
        return pred

    @torch.inference_mode()
    def predict_batch(self, images: list[np.ndarray]) -> list[Prediction]:
        tensors = torch.cat([self.preprocess(img) for img in images], dim=0).to(self.device)
        outputs = self.model(tensors)
        preds = []
        for i, img in enumerate(images):
            out_i = outputs[i].unsqueeze(0) if outputs.dim() > 1 else outputs
            preds.append(self.postprocess(out_i, img.shape[:2]))
        return preds

    def train_mode(self) -> None:
        self.model.train()

    def eval_mode(self) -> None:
        self.model.eval()

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({"state_dict": self.model.state_dict(), "config": self.config.to_dict()}, path)

    def load(self, path: str | Path) -> None:
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(ckpt["state_dict"])
        self.model.to(self.device)
        self.model.eval()

    def parameter_count(self) -> dict[str, int]:
        total = sum(p.numel() for p in self.model.parameters())
        trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
        return {"total": total, "trainable": trainable, "frozen": total - trainable}

    # --- private --------------------------------------------------------------

    @staticmethod
    def _resolve_device(device: str) -> torch.device:
        if device == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return torch.device("mps")
            return torch.device("cpu")
        return torch.device(device)
