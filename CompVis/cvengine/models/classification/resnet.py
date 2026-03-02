"""ResNet family wrappers (resnet18/34/50/101/152) with transfer learning."""

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
    "resnet18": models.resnet18,
    "resnet34": models.resnet34,
    "resnet50": models.resnet50,
    "resnet101": models.resnet101,
    "resnet152": models.resnet152,
}

_WEIGHTS = {
    "resnet18": models.ResNet18_Weights.DEFAULT,
    "resnet34": models.ResNet34_Weights.DEFAULT,
    "resnet50": models.ResNet50_Weights.DEFAULT,
    "resnet101": models.ResNet101_Weights.DEFAULT,
    "resnet152": models.ResNet152_Weights.DEFAULT,
}


def _make_resnet(variant: str):
    """Factory registered for each resnet variant."""

    @ModelRegistry.register(variant, task="classification", family="resnet")
    class _ResNet(ResNetWrapper):
        _variant = variant
    _ResNet.__name__ = f"ResNet_{variant}"
    _ResNet.__qualname__ = _ResNet.__name__
    return _ResNet


class ResNetWrapper(BaseModel):
    _variant: str = "resnet50"

    @property
    def task_type(self) -> TaskType:
        return TaskType.CLASSIFICATION

    def build_model(self, config: Config) -> nn.Module:
        name = config.get("model.name", self._variant)
        variant = name if name in _VARIANTS else self._variant
        pretrained = config.get("model.pretrained", True)
        num_classes = config.get("model.num_classes", 1000)

        weights = _WEIGHTS[variant] if pretrained else None
        model = _VARIANTS[variant](weights=weights)

        if num_classes != 1000:
            model.fc = nn.Linear(model.fc.in_features, num_classes)

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
        elif len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
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


# Auto-register every variant
for _v in _VARIANTS:
    _make_resnet(_v)
