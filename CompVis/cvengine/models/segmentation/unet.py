"""U-Net implementation for semantic segmentation."""

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


class _DoubleConv(nn.Module):
    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class _UNet(nn.Module):
    def __init__(self, in_channels: int = 3, num_classes: int = 2,
                 base_features: int = 64):
        super().__init__()
        f = base_features
        self.enc1 = _DoubleConv(in_channels, f)
        self.enc2 = _DoubleConv(f, f * 2)
        self.enc3 = _DoubleConv(f * 2, f * 4)
        self.enc4 = _DoubleConv(f * 4, f * 8)
        self.pool = nn.MaxPool2d(2)
        self.bottleneck = _DoubleConv(f * 8, f * 16)
        self.up4 = nn.ConvTranspose2d(f * 16, f * 8, 2, stride=2)
        self.dec4 = _DoubleConv(f * 16, f * 8)
        self.up3 = nn.ConvTranspose2d(f * 8, f * 4, 2, stride=2)
        self.dec3 = _DoubleConv(f * 8, f * 4)
        self.up2 = nn.ConvTranspose2d(f * 4, f * 2, 2, stride=2)
        self.dec2 = _DoubleConv(f * 4, f * 2)
        self.up1 = nn.ConvTranspose2d(f * 2, f, 2, stride=2)
        self.dec1 = _DoubleConv(f * 2, f)
        self.head = nn.Conv2d(f, num_classes, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        b = self.bottleneck(self.pool(e4))
        d4 = self.dec4(torch.cat([self.up4(b), e4], dim=1))
        d3 = self.dec3(torch.cat([self.up3(d4), e3], dim=1))
        d2 = self.dec2(torch.cat([self.up2(d3), e2], dim=1))
        d1 = self.dec1(torch.cat([self.up1(d2), e1], dim=1))
        return self.head(d1)


@ModelRegistry.register("unet", task="segmentation", family="unet")
class UNetWrapper(BaseModel):
    @property
    def task_type(self) -> TaskType:
        return TaskType.SEGMENTATION

    def build_model(self, config: Config) -> nn.Module:
        self._num_classes = config.get("model.num_classes", 2)
        self._image_size = config.get("data.image_size", 256)
        self._labels: dict[int, str] | None = config.get("model.class_map")
        self._transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((self._image_size, self._image_size), antialias=True),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        return _UNet(
            in_channels=config.get("model.in_channels", 3),
            num_classes=self._num_classes,
            base_features=config.get("model.base_features", 64),
        )

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        return self._transform(image).unsqueeze(0)

    def postprocess(self, output: torch.Tensor, original_shape: tuple[int, ...]) -> Prediction:
        mask = output[0].argmax(dim=0).cpu().numpy().astype(np.uint8)
        h, w = original_shape[:2]
        mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return Prediction(
            task=TaskType.SEGMENTATION,
            mask=mask,
            class_map=self._labels,
        )
