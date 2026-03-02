"""Minimal SSD-style detector for rapid prototyping on custom datasets."""

from __future__ import annotations

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.ops import nms

from cvengine.core.base import BaseModel
from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import BoundingBox, Prediction, TaskType


class _MiniDetector(nn.Module):
    """Feature-pyramid-lite single-shot detector for hackathon prototyping."""

    def __init__(self, num_classes: int):
        super().__init__()
        self.backbone = nn.Sequential(
            nn.Conv2d(3, 32, 3, stride=2, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.Conv2d(32, 64, 3, stride=2, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.Conv2d(64, 128, 3, stride=2, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.Conv2d(128, 256, 3, stride=2, padding=1), nn.BatchNorm2d(256), nn.ReLU(),
        )
        # Per-cell predictions: 4 bbox coords + num_classes confidence
        self.head = nn.Conv2d(256, 4 + num_classes, 1)
        self._num_classes = num_classes

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        feat = self.backbone(x)
        out = self.head(feat)  # (B, 4+C, H', W')
        return out


@ModelRegistry.register("custom_detector", task="detection", family="custom")
class CustomDetector(BaseModel):
    @property
    def task_type(self) -> TaskType:
        return TaskType.DETECTION

    def build_model(self, config: Config) -> nn.Module:
        self._num_classes = config.get("model.num_classes", 20)
        self._image_size = config.get("data.image_size", 256)
        self._conf = config.get("inference.confidence_threshold", 0.5)
        self._iou = config.get("inference.nms_threshold", 0.45)
        self._labels: list[str] | None = config.get("model.labels")
        self._transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Resize((self._image_size, self._image_size), antialias=True),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        return _MiniDetector(self._num_classes)

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        return self._transform(image).unsqueeze(0)

    def postprocess(self, output: torch.Tensor, original_shape: tuple[int, ...]) -> Prediction:
        h_orig, w_orig = original_shape[:2]
        B, C, H, W = output.shape
        out = output[0]  # (4+num_cls, H', W')

        coords = out[:4]  # (4, H', W')
        class_logits = out[4:]  # (num_cls, H', W')
        class_probs = torch.sigmoid(class_logits)

        max_probs, class_ids = class_probs.max(dim=0)  # (H', W')
        mask = max_probs > self._conf

        if mask.sum() == 0:
            return Prediction(task=TaskType.DETECTION, boxes=[])

        # Grid offsets
        gy, gx = torch.meshgrid(torch.arange(H, device=output.device),
                                 torch.arange(W, device=output.device), indexing="ij")
        cx = (gx[mask].float() + torch.sigmoid(coords[0][mask])) / W * w_orig
        cy = (gy[mask].float() + torch.sigmoid(coords[1][mask])) / H * h_orig
        bw = torch.exp(coords[2][mask].clamp(-5, 5)) / W * w_orig
        bh = torch.exp(coords[3][mask].clamp(-5, 5)) / H * h_orig

        x1 = cx - bw / 2
        y1 = cy - bh / 2
        x2 = cx + bw / 2
        y2 = cy + bh / 2

        xyxy = torch.stack([x1, y1, x2, y2], dim=-1)
        scores = max_probs[mask]
        cids = class_ids[mask]

        keep = nms(xyxy, scores, self._iou)
        boxes = []
        for k in keep:
            cid = int(cids[k])
            boxes.append(BoundingBox(
                x1=float(x1[k]), y1=float(y1[k]), x2=float(x2[k]), y2=float(y2[k]),
                confidence=float(scores[k]),
                class_id=cid,
                class_name=self._labels[cid] if self._labels else str(cid),
            ))
        return Prediction(task=TaskType.DETECTION, boxes=boxes)
