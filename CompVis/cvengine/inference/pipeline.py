"""High-level inference pipeline: config -> model -> predict.

This is the primary entry point for users who just want quick results:

    pipe = InferencePipeline.from_config("configs/detection.yaml")
    result = pipe("path/to/image.jpg")
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

import cvengine.models  # noqa: F401  — trigger auto-registration
from cvengine.core.config import Config
from cvengine.core.base import BaseModel
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import Prediction
from cvengine.utils.io import load_image
from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class InferencePipeline:
    """Load a model from config and run inference on images."""

    def __init__(self, model: BaseModel, config: Config):
        self.model = model
        self.config = config
        params = model.parameter_count()
        log.info("Pipeline ready | model=%s | device=%s | params=%s",
                 config.get("model.name"), model.device, f"{params['total']:,}")

    @classmethod
    def from_config(cls, config_path: str | Path | None = None,
                    config_dict: dict | None = None,
                    cli_overrides: list[str] | None = None) -> InferencePipeline:
        if config_path:
            cfg = Config.from_yaml(config_path)
        elif config_dict:
            cfg = Config.from_dict(config_dict)
        else:
            cfg = Config()
        if cli_overrides:
            cfg = cfg.merge_cli(cli_overrides)

        model_name = cfg.get("model.name", "resnet50")
        model_cls = ModelRegistry.get(model_name)
        model_instance = model_cls(cfg)
        return cls(model_instance, cfg)

    def __call__(self, source: str | Path | np.ndarray | bytes) -> Prediction:
        if isinstance(source, np.ndarray):
            image = source
        else:
            image = load_image(source, color="rgb")
        return self.model.predict(image)

    def predict_batch(self, sources: list[str | Path | np.ndarray]) -> list[Prediction]:
        images = []
        for s in sources:
            if isinstance(s, np.ndarray):
                images.append(s)
            else:
                images.append(load_image(s, color="rgb"))
        return self.model.predict_batch(images)

    def warmup(self, size: tuple[int, int] = (224, 224)) -> None:
        dummy = np.random.randint(0, 255, (*size, 3), dtype=np.uint8)
        self.model.predict(dummy)
        log.info("Warmup complete")
