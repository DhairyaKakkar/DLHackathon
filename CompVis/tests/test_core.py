"""Tests for core modules: Config, Registry, Types."""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry, _Registry
from cvengine.core.types import BoundingBox, Prediction, TaskType


class TestConfig:
    def test_defaults(self):
        cfg = Config()
        assert cfg.get("task") == "classification"
        assert cfg.get("model.name") == "resnet50"
        assert cfg.get("training.lr") == 1e-3

    def test_from_dict(self):
        cfg = Config.from_dict({"model": {"name": "yolov8n"}, "task": "detection"})
        assert cfg.get("model.name") == "yolov8n"
        assert cfg.get("task") == "detection"
        # defaults preserved
        assert cfg.get("training.lr") == 1e-3

    def test_yaml_roundtrip(self, tmp_path):
        cfg = Config.from_dict({"model": {"name": "test"}, "training": {"epochs": 42}})
        path = tmp_path / "test.yaml"
        cfg.save(path)
        loaded = Config.from_yaml(path)
        assert loaded.get("model.name") == "test"
        assert loaded.get("training.epochs") == 42

    def test_merge(self):
        cfg = Config()
        merged = cfg.merge({"training": {"lr": 0.01}})
        assert merged.get("training.lr") == 0.01
        # Original unchanged
        assert cfg.get("training.lr") == 1e-3

    def test_cli_overrides(self):
        cfg = Config()
        merged = cfg.merge_cli(["training.lr=0.005", "model.name=resnet18", "training.epochs=5"])
        assert merged.get("training.lr") == 0.005
        assert merged.get("model.name") == "resnet18"
        assert merged.get("training.epochs") == 5

    def test_set(self):
        cfg = Config()
        cfg.set("model.name", "new_model")
        assert cfg.get("model.name") == "new_model"

    def test_get_missing_returns_default(self):
        cfg = Config()
        assert cfg.get("nonexistent.key", "fallback") == "fallback"


class TestRegistry:
    def test_register_and_get(self):
        reg = _Registry("Test")

        @reg.register("foo", meta="bar")
        class Foo:
            pass

        assert reg.get("foo") is Foo
        assert "foo" in reg
        assert reg.get_meta("foo") == {"meta": "bar"}

    def test_missing_key_raises(self):
        reg = _Registry("Test")
        with pytest.raises(KeyError, match="not found"):
            reg.get("missing")


class TestBoundingBox:
    def test_properties(self):
        box = BoundingBox(10, 20, 110, 120, confidence=0.9, class_id=1, class_name="cat")
        assert box.width == 100
        assert box.height == 100
        assert box.area == 10000
        assert box.center == (60, 70)

    def test_iou_identical(self):
        box = BoundingBox(0, 0, 100, 100)
        assert box.iou(box) == pytest.approx(1.0)

    def test_iou_no_overlap(self):
        a = BoundingBox(0, 0, 50, 50)
        b = BoundingBox(100, 100, 200, 200)
        assert a.iou(b) == 0.0

    def test_iou_partial(self):
        a = BoundingBox(0, 0, 100, 100)
        b = BoundingBox(50, 50, 150, 150)
        # intersection = 50*50 = 2500, union = 10000+10000-2500 = 17500
        assert a.iou(b) == pytest.approx(2500 / 17500)


class TestPrediction:
    def test_classification_to_dict(self):
        pred = Prediction(task=TaskType.CLASSIFICATION, class_id=5,
                          class_name="dog", confidence=0.95)
        d = pred.to_dict()
        assert d["task"] == "classification"
        assert d["class_name"] == "dog"

    def test_detection_to_dict(self):
        boxes = [BoundingBox(0, 0, 50, 50, 0.9, 0, "cat")]
        pred = Prediction(task=TaskType.DETECTION, boxes=boxes)
        d = pred.to_dict()
        assert len(d["boxes"]) == 1
