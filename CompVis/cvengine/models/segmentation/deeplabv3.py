"""DeepLabV3 wrapper using torchvision pretrained models."""

from __future__ import annotations

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms
from torchvision.models.segmentation import (
    DeepLabV3_ResNet50_Weights,
    DeepLabV3_ResNet101_Weights,
)

from cvengine.core.base import BaseModel
from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import Prediction, TaskType

_VARIANTS = {
    "deeplabv3_resnet50": (models.segmentation.deeplabv3_resnet50, DeepLabV3_ResNet50_Weights.DEFAULT),
    "deeplabv3_resnet101": (models.segmentation.deeplabv3_resnet101, DeepLabV3_ResNet101_Weights.DEFAULT),
}


@ModelRegistry.register("deeplabv3_resnet50", task="segmentation", family="deeplab")
@ModelRegistry.register("deeplabv3_resnet101", task="segmentation", family="deeplab")
class DeepLabV3Wrapper(BaseModel):
    @property
    def task_type(self) -> TaskType:
        return TaskType.SEGMENTATION

    def build_model(self, config: Config) -> nn.Module:
        name = config.get("model.name", "deeplabv3_resnet50")
        pretrained = config.get("model.pretrained", True)
        factory, weights = _VARIANTS.get(name, _VARIANTS["deeplabv3_resnet50"])
        model = factory(weights=weights if pretrained else None)
        self._image_size = config.get("data.image_size", 520)
        self._transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        return model

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        return self._transform(image).unsqueeze(0)

    def postprocess(self, output: dict, original_shape: tuple[int, ...]) -> Prediction:
        logits = output["out"][0]  # (num_classes, H, W)
        mask = logits.argmax(dim=0).cpu().numpy().astype(np.uint8)
        h, w = original_shape[:2]
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return Prediction(task=TaskType.SEGMENTATION, mask=mask)
