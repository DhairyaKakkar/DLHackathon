"""Model ensemble wrapper for combining predictions from multiple models."""

from __future__ import annotations

import time
from collections import Counter
from typing import Any

import numpy as np
import torch

from cvengine.core.base import BaseModel
from cvengine.core.config import Config
from cvengine.core.types import BoundingBox, Prediction, TaskType
from cvengine.inference.pipeline import InferencePipeline
from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class EnsembleModel:
    """Combine predictions from multiple InferencePipelines.

    Strategies:
        - classification: majority vote or average probabilities
        - detection: merge boxes with WBF (weighted boxes fusion) style
        - segmentation: pixel-wise majority vote
    """

    def __init__(self, pipelines: list[InferencePipeline],
                 strategy: str = "average"):
        """
        Args:
            pipelines: list of InferencePipelines (all same task type).
            strategy: 'vote', 'average' (classification), or 'union' (detection).
        """
        self.pipelines = pipelines
        self.strategy = strategy

    def predict(self, image: np.ndarray) -> Prediction:
        t0 = time.perf_counter()
        preds = [p(image) for p in self.pipelines]
        task = preds[0].task

        if task == TaskType.CLASSIFICATION:
            result = self._ensemble_classification(preds)
        elif task == TaskType.DETECTION:
            result = self._ensemble_detection(preds)
        elif task == TaskType.SEGMENTATION:
            result = self._ensemble_segmentation(preds)
        else:
            result = preds[0]

        result.inference_time_ms = (time.perf_counter() - t0) * 1000
        return result

    def _ensemble_classification(self, preds: list[Prediction]) -> Prediction:
        if self.strategy == "vote":
            votes = Counter(p.class_id for p in preds)
            best_id, count = votes.most_common(1)[0]
            best_pred = next(p for p in preds if p.class_id == best_id)
            return Prediction(
                task=TaskType.CLASSIFICATION,
                class_id=best_id,
                class_name=best_pred.class_name,
                confidence=count / len(preds),
                metadata={"ensemble_strategy": "vote", "n_models": len(preds)},
            )
        # average probabilities
        all_topk = [p.top_k for p in preds if p.top_k]
        if not all_topk:
            return preds[0]
        score_map: dict[int, list[float]] = {}
        name_map: dict[int, str] = {}
        for topk in all_topk:
            for entry in topk:
                cid = entry["class_id"]
                score_map.setdefault(cid, []).append(entry["confidence"])
                name_map[cid] = entry["class_name"]
        avg_scores = {cid: sum(s) / len(preds) for cid, s in score_map.items()}
        best_id = max(avg_scores, key=avg_scores.get)  # type: ignore[arg-type]
        return Prediction(
            task=TaskType.CLASSIFICATION,
            class_id=best_id,
            class_name=name_map[best_id],
            confidence=avg_scores[best_id],
            metadata={"ensemble_strategy": "average", "n_models": len(preds)},
        )

    def _ensemble_detection(self, preds: list[Prediction]) -> Prediction:
        all_boxes: list[BoundingBox] = []
        for p in preds:
            if p.boxes:
                all_boxes.extend(p.boxes)
        # Simple NMS-style dedup: keep highest confidence per overlapping cluster
        all_boxes.sort(key=lambda b: b.confidence, reverse=True)
        keep: list[BoundingBox] = []
        used = [False] * len(all_boxes)
        for i, box in enumerate(all_boxes):
            if used[i]:
                continue
            keep.append(box)
            for j in range(i + 1, len(all_boxes)):
                if not used[j] and box.iou(all_boxes[j]) > 0.5:
                    used[j] = True
        return Prediction(task=TaskType.DETECTION, boxes=keep,
                          metadata={"ensemble_strategy": "union", "n_models": len(preds)})

    def _ensemble_segmentation(self, preds: list[Prediction]) -> Prediction:
        masks = [p.mask for p in preds if p.mask is not None]
        if not masks:
            return preds[0]
        stacked = np.stack(masks, axis=0)
        from scipy import stats
        majority, _ = stats.mode(stacked, axis=0, keepdims=False)
        return Prediction(task=TaskType.SEGMENTATION, mask=majority.astype(np.uint8),
                          metadata={"ensemble_strategy": "majority_vote", "n_models": len(preds)})
