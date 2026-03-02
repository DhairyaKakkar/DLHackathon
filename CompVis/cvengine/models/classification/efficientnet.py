"""EfficientNet family wrappers with transfer learning support."""

from __future__ import annotations

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms

from cvengine.core.base import BaseModel
from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import Prediction, TaskType

_VARIANTS = {
    "efficientnet_b0": (models.efficientnet_b0, models.EfficientNet_B0_Weights.DEFAULT),
    "efficientnet_b1": (models.efficientnet_b1, models.EfficientNet_B1_Weights.DEFAULT),
    "efficientnet_b2": (models.efficientnet_b2, models.EfficientNet_B2_Weights.DEFAULT),
    "efficientnet_b3": (models.efficientnet_b3, models.EfficientNet_B3_Weights.DEFAULT),
    "efficientnet_b4": (models.efficientnet_b4, models.EfficientNet_B4_Weights.DEFAULT),
}


def _make_effnet(variant: str):
    @ModelRegistry.register(variant, task="classification", family="efficientnet")
    class _EffNet(EfficientNetWrapper):
        _variant = variant
    _EffNet.__name__ = f"EfficientNet_{variant}"
    _EffNet.__qualname__ = _EffNet.__name__
    return _EffNet


class EfficientNetWrapper(BaseModel):
    _variant: str = "efficientnet_b0"

    @property
    def task_type(self) -> TaskType:
        return TaskType.CLASSIFICATION

    def build_model(self, config: Config) -> nn.Module:
        variant = config.get("model.name", self._variant)
        if variant not in _VARIANTS:
            variant = self._variant
        pretrained = config.get("model.pretrained", True)
        num_classes = config.get("model.num_classes", 1000)

        factory, weights = _VARIANTS[variant]
        model = factory(weights=weights if pretrained else None)

        if num_classes != 1000:
            in_features = model.classifier[-1].in_features
            model.classifier[-1] = nn.Linear(in_features, num_classes)

        self._image_size = config.get("data.image_size", 224)
        self._labels: list[str] | None = config.get("model.labels")
        self._transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((self._image_size, self._image_size), antialias=True),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        return model

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGB)
        tensor = self._transform(image)
        return tensor.unsqueeze(0)

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


for _v in _VARIANTS:
    _make_effnet(_v)
