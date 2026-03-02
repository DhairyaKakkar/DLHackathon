"""Custom lightweight classifier for rapid prototyping and small datasets."""

from __future__ import annotations

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms

from cvengine.core.base import BaseModel
from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import Prediction, TaskType


class _SimpleConvNet(nn.Module):
    """Quick 4-layer CNN for datasets < 10k images. Great for hackathon baselines."""

    def __init__(self, num_classes: int, in_channels: int = 3):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(4),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, 256), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.features(x))


@ModelRegistry.register("custom_classifier", task="classification", family="custom")
class CustomClassifier(BaseModel):
    @property
    def task_type(self) -> TaskType:
        return TaskType.CLASSIFICATION

    def build_model(self, config: Config) -> nn.Module:
        num_classes = config.get("model.num_classes", 10)
        in_channels = config.get("model.in_channels", 3)
        self._image_size = config.get("data.image_size", 64)
        self._labels: list[str] | None = config.get("model.labels")
        self._transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((self._image_size, self._image_size), antialias=True),
            transforms.Normalize(mean=[0.5] * in_channels, std=[0.5] * in_channels),
        ])
        return _SimpleConvNet(num_classes, in_channels)

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        return self._transform(image).unsqueeze(0)

    def postprocess(self, output: torch.Tensor, original_shape: tuple[int, ...]) -> Prediction:
        probs = torch.softmax(output, dim=-1)[0]
        topk_vals, topk_ids = probs.topk(min(5, probs.shape[0]))
        top = []
        for v, i in zip(topk_vals.tolist(), topk_ids.tolist()):
            name = self._labels[i] if self._labels else str(i)
            top.append({"class_id": i, "class_name": name, "confidence": v})
        best = top[0]
        return Prediction(
            task=TaskType.CLASSIFICATION,
            class_id=best["class_id"],
            class_name=best["class_name"],
            confidence=best["confidence"],
            top_k=top,
        )
