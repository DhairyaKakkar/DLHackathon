"""Evaluation metrics for classification, detection, and segmentation."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

import numpy as np

from cvengine.core.types import BoundingBox, Prediction, TaskType


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

def accuracy(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return correct / max(len(y_true), 1)


def precision_recall_f1(
    y_true: Sequence[int], y_pred: Sequence[int], num_classes: int | None = None,
) -> dict[str, Any]:
    classes = sorted(set(y_true) | set(y_pred))
    if num_classes:
        classes = list(range(num_classes))
    per_class: dict[int, dict[str, float]] = {}
    for c in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == c and p == c)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != c and p == c)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == c and p != c)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        per_class[c] = {"precision": prec, "recall": rec, "f1": f1}
    macro_p = np.mean([v["precision"] for v in per_class.values()])
    macro_r = np.mean([v["recall"] for v in per_class.values()])
    macro_f1 = np.mean([v["f1"] for v in per_class.values()])
    return {
        "per_class": per_class,
        "macro_precision": float(macro_p),
        "macro_recall": float(macro_r),
        "macro_f1": float(macro_f1),
    }


def confusion_matrix(y_true: Sequence[int], y_pred: Sequence[int],
                     num_classes: int | None = None) -> np.ndarray:
    classes = sorted(set(y_true) | set(y_pred))
    n = num_classes or (max(classes) + 1 if classes else 0)
    cm = np.zeros((n, n), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    return cm


class ClassificationEvaluator:
    """Accumulate predictions and compute all classification metrics at once."""

    def __init__(self):
        self._true: list[int] = []
        self._pred: list[int] = []
        self._confs: list[float] = []

    def update(self, pred: Prediction, ground_truth: int) -> None:
        self._true.append(ground_truth)
        self._pred.append(pred.class_id or 0)
        self._confs.append(pred.confidence or 0.0)

    def compute(self) -> dict[str, Any]:
        return {
            "accuracy": accuracy(self._true, self._pred),
            **precision_recall_f1(self._true, self._pred),
            "confusion_matrix": confusion_matrix(self._true, self._pred).tolist(),
            "n_samples": len(self._true),
        }


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def _compute_ap(recalls: np.ndarray, precisions: np.ndarray) -> float:
    """11-point interpolated AP."""
    ap = 0.0
    for t in np.arange(0, 1.1, 0.1):
        mask = recalls >= t
        if mask.any():
            ap += precisions[mask].max()
    return ap / 11


def mean_ap(
    predictions: list[list[BoundingBox]],
    ground_truths: list[list[BoundingBox]],
    iou_threshold: float = 0.5,
) -> dict[str, float]:
    """Compute mAP@IoU for a set of images.

    Each entry in predictions/ground_truths is the list of boxes for one image.
    """
    # Collect per-class detections
    class_dets: dict[int, list[dict]] = defaultdict(list)
    class_gts: dict[int, list[dict]] = defaultdict(list)

    for img_idx, (pboxes, gboxes) in enumerate(zip(predictions, ground_truths)):
        for box in pboxes:
            class_dets[box.class_id].append({"img": img_idx, "box": box, "conf": box.confidence})
        for box in gboxes:
            class_gts[box.class_id].append({"img": img_idx, "box": box, "matched": False})

    aps: dict[int, float] = {}
    for cid in sorted(set(class_dets) | set(class_gts)):
        dets = sorted(class_dets.get(cid, []), key=lambda d: d["conf"], reverse=True)
        gts = class_gts.get(cid, [])
        n_gt = len(gts)
        if n_gt == 0:
            continue

        # Reset matched flags
        for g in gts:
            g["matched"] = False

        tp = np.zeros(len(dets))
        fp = np.zeros(len(dets))

        for i, det in enumerate(dets):
            best_iou = 0.0
            best_gt = -1
            for j, gt in enumerate(gts):
                if gt["img"] != det["img"]:
                    continue
                iou = det["box"].iou(gt["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_gt = j
            if best_iou >= iou_threshold and best_gt >= 0 and not gts[best_gt]["matched"]:
                tp[i] = 1
                gts[best_gt]["matched"] = True
            else:
                fp[i] = 1

        cum_tp = np.cumsum(tp)
        cum_fp = np.cumsum(fp)
        recalls = cum_tp / n_gt
        precisions = cum_tp / (cum_tp + cum_fp)
        aps[cid] = _compute_ap(recalls, precisions)

    map_val = float(np.mean(list(aps.values()))) if aps else 0.0
    return {"mAP": map_val, "per_class_ap": {k: float(v) for k, v in aps.items()}}


class DetectionEvaluator:
    def __init__(self, iou_threshold: float = 0.5):
        self._preds: list[list[BoundingBox]] = []
        self._gts: list[list[BoundingBox]] = []
        self._iou = iou_threshold

    def update(self, pred: Prediction, gt_boxes: list[BoundingBox]) -> None:
        self._preds.append(pred.boxes or [])
        self._gts.append(gt_boxes)

    def compute(self) -> dict[str, Any]:
        return mean_ap(self._preds, self._gts, self._iou)


# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def mean_iou(pred_mask: np.ndarray, gt_mask: np.ndarray,
             num_classes: int | None = None) -> dict[str, float]:
    classes = sorted(set(np.unique(pred_mask)) | set(np.unique(gt_mask)))
    if num_classes:
        classes = list(range(num_classes))
    ious: dict[int, float] = {}
    for c in classes:
        intersection = np.sum((pred_mask == c) & (gt_mask == c))
        union = np.sum((pred_mask == c) | (gt_mask == c))
        ious[c] = float(intersection / union) if union > 0 else 0.0
    return {
        "mean_iou": float(np.mean(list(ious.values()))) if ious else 0.0,
        "per_class_iou": ious,
    }
