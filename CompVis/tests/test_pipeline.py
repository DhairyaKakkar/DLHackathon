"""Tests for the inference pipeline and evaluation metrics."""

import numpy as np
import pytest

from cvengine.core.config import Config
from cvengine.core.types import BoundingBox, Prediction, TaskType
from cvengine.evaluation.metrics import accuracy, precision_recall_f1, mean_iou, mean_ap
from cvengine.evaluation.calibration import expected_calibration_error
from cvengine.inference.pipeline import InferencePipeline
from cvengine.advanced.drift import DriftDetector


class TestInferencePipeline:
    def test_from_config_dict(self):
        pipe = InferencePipeline.from_config(config_dict={
            "model": {"name": "resnet18", "pretrained": True},
            "inference": {"device": "cpu"},
        })
        assert pipe.model is not None

    def test_predict_numpy(self):
        pipe = InferencePipeline.from_config(config_dict={
            "model": {"name": "resnet18", "pretrained": True},
            "inference": {"device": "cpu"},
        })
        img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        pred = pipe(img)
        assert pred.task == TaskType.CLASSIFICATION


class TestMetrics:
    def test_accuracy(self):
        assert accuracy([0, 1, 2, 0, 1], [0, 1, 2, 0, 1]) == 1.0
        assert accuracy([0, 1, 2], [1, 1, 1]) == pytest.approx(1 / 3)

    def test_precision_recall_f1(self):
        y_true = [0, 0, 1, 1, 2, 2]
        y_pred = [0, 0, 1, 0, 2, 2]
        result = precision_recall_f1(y_true, y_pred)
        assert result["per_class"][0]["precision"] == pytest.approx(2 / 3)
        assert result["per_class"][1]["recall"] == pytest.approx(0.5)

    def test_mean_iou(self):
        gt = np.array([[0, 1], [1, 0]])
        pred = np.array([[0, 1], [0, 0]])
        result = mean_iou(pred, gt)
        assert 0 <= result["mean_iou"] <= 1

    def test_mean_ap(self):
        preds = [[BoundingBox(10, 10, 50, 50, 0.9, 0, "a")]]
        gts = [[BoundingBox(10, 10, 50, 50, 1.0, 0, "a")]]
        result = mean_ap(preds, gts, iou_threshold=0.5)
        assert result["mAP"] > 0

    def test_ece(self):
        confs = np.array([0.9, 0.8, 0.7, 0.6])
        preds = np.array([1, 1, 0, 0])
        labels = np.array([1, 1, 0, 1])
        ece = expected_calibration_error(confs, preds, labels, n_bins=5)
        assert 0 <= ece <= 1


class TestDriftDetector:
    def test_no_drift_on_stable_data(self):
        dd = DriftDetector(window_size=50, threshold=100)
        alerts = [dd.update(0.9) for _ in range(50)]
        assert not any(alerts)

    def test_drift_on_sudden_drop(self):
        dd = DriftDetector(window_size=50, threshold=0.5)
        # Stable high confidence
        for _ in range(100):
            dd.update(0.95)
        # Sudden drop — large enough delta should trigger quickly
        detected = False
        for _ in range(200):
            if dd.update(0.1):
                detected = True
                break
        assert detected
