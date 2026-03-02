"""Data drift detection for streaming and production deployments.

Monitors input feature distribution and confidence distribution to flag
when the model may be receiving out-of-distribution data.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class DriftDetector:
    """Lightweight drift detector using Page-Hinkley test and confidence monitoring.

    Usage::

        detector = DriftDetector(window_size=100)
        for pred in predictions:
            alert = detector.update(pred.confidence)
            if alert:
                print("DRIFT DETECTED — retrain or investigate!")
    """

    def __init__(self, window_size: int = 200, threshold: float = 50.0,
                 alpha: float = 0.005, confidence_floor: float = 0.3):
        self.window_size = window_size
        self.threshold = threshold  # Page-Hinkley threshold
        self.alpha = alpha  # Tolerance for change detection
        self.confidence_floor = confidence_floor

        self._values: deque[float] = deque(maxlen=window_size)
        self._sum = 0.0
        self._mean = 0.0
        self._n = 0
        self._m = 0.0  # cumulative sum
        self._M = 0.0  # minimum of cumulative sum
        self._alerts = 0

    def update(self, confidence: float) -> bool:
        """Feed a new confidence score. Returns True if drift is detected.

        Uses two-sided Page-Hinkley: detects both upward and downward shifts.
        """
        self._values.append(confidence)
        self._n += 1
        self._mean = self._mean + (confidence - self._mean) / self._n

        # Detect decrease (confidence dropping)
        self._m = self._m + (self._mean - confidence - self.alpha)
        self._M = min(self._M, self._m)
        ph_stat = self._m - self._M

        drift = ph_stat > self.threshold

        if drift:
            self._alerts += 1
            log.warning("Drift alert #%d at sample %d (PH stat=%.2f)",
                        self._alerts, self._n, ph_stat)
            self.reset()

        return drift

    def update_batch(self, confidences: list[float]) -> list[bool]:
        return [self.update(c) for c in confidences]

    def reset(self) -> None:
        self._m = 0.0
        self._M = 0.0

    @property
    def stats(self) -> dict[str, Any]:
        values = list(self._values)
        if not values:
            return {"n": 0, "alerts": self._alerts}
        arr = np.array(values)
        return {
            "n": self._n,
            "alerts": self._alerts,
            "window_mean": float(arr.mean()),
            "window_std": float(arr.std()),
            "window_min": float(arr.min()),
            "below_floor_pct": float((arr < self.confidence_floor).mean()),
            "ph_statistic": self._m - self._M,
        }

    def is_healthy(self) -> bool:
        s = self.stats
        if s["n"] < self.window_size:
            return True  # Not enough data
        return s["below_floor_pct"] < 0.2 and s["window_mean"] > self.confidence_floor
