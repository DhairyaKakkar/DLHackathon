"""Tests for model wrappers — ensure they load and produce valid Predictions."""

import numpy as np
import pytest

from cvengine.core.config import Config
from cvengine.core.types import TaskType
import cvengine.models  # noqa: F401
from cvengine.core.registry import ModelRegistry


@pytest.fixture
def dummy_image():
    return np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)


class TestClassification:
    @pytest.mark.parametrize("model_name", ["resnet18", "resnet50"])
    def test_pretrained_prediction(self, model_name, dummy_image):
        cfg = Config.from_dict({
            "model": {"name": model_name, "pretrained": True, "num_classes": 1000},
            "inference": {"device": "cpu"},
        })
        cls = ModelRegistry.get(model_name)
        model = cls(cfg)
        pred = model.predict(dummy_image)

        assert pred.task == TaskType.CLASSIFICATION
        assert pred.class_id is not None
        assert pred.confidence is not None
        assert 0 <= pred.confidence <= 1
        assert pred.top_k is not None
        assert len(pred.top_k) == 5
        assert pred.inference_time_ms > 0

    def test_custom_classifier(self, dummy_image):
        cfg = Config.from_dict({
            "model": {"name": "custom_classifier", "num_classes": 5},
            "data": {"image_size": 64},
            "inference": {"device": "cpu"},
        })
        cls = ModelRegistry.get("custom_classifier")
        model = cls(cfg)
        pred = model.predict(dummy_image)
        assert pred.task == TaskType.CLASSIFICATION
        assert pred.top_k is not None
        assert len(pred.top_k) == 5

    def test_parameter_count(self, dummy_image):
        cfg = Config.from_dict({
            "model": {"name": "resnet18", "pretrained": False, "num_classes": 10},
            "inference": {"device": "cpu"},
        })
        cls = ModelRegistry.get("resnet18")
        model = cls(cfg)
        counts = model.parameter_count()
        assert counts["total"] > 0
        assert counts["trainable"] == counts["total"]


class TestSegmentation:
    def test_unet(self, dummy_image):
        cfg = Config.from_dict({
            "model": {"name": "unet", "num_classes": 2, "base_features": 16},
            "data": {"image_size": 64},
            "inference": {"device": "cpu"},
        })
        cls = ModelRegistry.get("unet")
        model = cls(cfg)
        pred = model.predict(dummy_image)
        assert pred.task == TaskType.SEGMENTATION
        assert pred.mask is not None
        assert pred.mask.shape == (224, 224)


class TestRegistryCompleteness:
    def test_all_models_registered(self):
        expected = {
            "resnet18", "resnet50", "efficientnet_b0",
            "custom_classifier", "custom_detector",
            "unet", "deeplabv3_resnet50",
            "tesseract", "easyocr",
        }
        registered = set(ModelRegistry.list_keys())
        for m in expected:
            assert m in registered, f"'{m}' not registered"
