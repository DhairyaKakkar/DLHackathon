"""Drawing utilities for bounding boxes, masks, and full prediction overlays."""

from __future__ import annotations

from typing import Sequence

import cv2
import numpy as np

from cvengine.core.types import BoundingBox, Prediction, TaskType


# 20 visually distinct colours (BGR)
_PALETTE = [
    (76, 153, 0), (0, 137, 255), (255, 0, 0), (0, 255, 255), (255, 127, 0),
    (204, 0, 204), (0, 204, 204), (128, 128, 0), (0, 0, 255), (255, 0, 127),
    (0, 255, 0), (255, 255, 0), (128, 0, 255), (255, 128, 128), (0, 128, 255),
    (128, 255, 0), (255, 0, 255), (0, 255, 128), (128, 0, 0), (0, 0, 128),
]


def draw_boxes(image: np.ndarray, boxes: Sequence[BoundingBox],
               thickness: int = 2, font_scale: float = 0.5) -> np.ndarray:
    canvas = image.copy()
    for box in boxes:
        color = _PALETTE[box.class_id % len(_PALETTE)]
        pt1 = (int(box.x1), int(box.y1))
        pt2 = (int(box.x2), int(box.y2))
        cv2.rectangle(canvas, pt1, pt2, color, thickness)
        label = f"{box.class_name} {box.confidence:.2f}" if box.class_name else f"{box.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        cv2.rectangle(canvas, pt1, (pt1[0] + tw, pt1[1] - th - 4), color, -1)
        cv2.putText(canvas, label, (pt1[0], pt1[1] - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1)
    return canvas


def draw_mask(image: np.ndarray, mask: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    canvas = image.copy()
    unique_ids = np.unique(mask)
    for cid in unique_ids:
        if cid == 0:
            continue
        color = _PALETTE[int(cid) % len(_PALETTE)]
        overlay = canvas.copy()
        overlay[mask == cid] = color
        cv2.addWeighted(overlay, alpha, canvas, 1 - alpha, 0, canvas)
    return canvas


def draw_predictions(image: np.ndarray, pred: Prediction) -> np.ndarray:
    if pred.task == TaskType.CLASSIFICATION:
        label = f"{pred.class_name}: {pred.confidence:.2f}" if pred.class_name else ""
        canvas = image.copy()
        cv2.putText(canvas, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        return canvas
    if pred.task == TaskType.DETECTION and pred.boxes:
        return draw_boxes(image, pred.boxes)
    if pred.task == TaskType.SEGMENTATION and pred.mask is not None:
        return draw_mask(image, pred.mask)
    if pred.task == TaskType.OCR:
        canvas = image.copy()
        text = pred.text or ""
        y = 30
        for line in text.split("\n"):
            cv2.putText(canvas, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
            y += 25
        return canvas
    return image.copy()
