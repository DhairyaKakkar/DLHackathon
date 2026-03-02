"""OCR wrappers for Tesseract and EasyOCR."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import torch
import torch.nn as nn

from cvengine.core.base import BaseModel
from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import Prediction, TaskType


class _DummyModule(nn.Module):
    """Placeholder nn.Module for non-torch OCR backends."""
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x


@ModelRegistry.register("tesseract", task="ocr", family="tesseract")
class TesseractOCR(BaseModel):
    """pytesseract-based OCR. Install: pip install pytesseract + system Tesseract."""

    @property
    def task_type(self) -> TaskType:
        return TaskType.OCR

    def build_model(self, config: Config) -> nn.Module:
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            raise ImportError("Install pytesseract: pip install pytesseract")
        self._lang = config.get("model.lang", "eng")
        self._psm = config.get("model.psm", 3)
        return _DummyModule()

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        return torch.empty(0)

    @torch.inference_mode()
    def predict(self, image: np.ndarray) -> Prediction:
        import pytesseract

        t0 = time.perf_counter()
        custom_config = f"--psm {self._psm}"
        text = pytesseract.image_to_string(image, lang=self._lang, config=custom_config)
        data = pytesseract.image_to_data(image, lang=self._lang, config=custom_config,
                                         output_type=pytesseract.Output.DICT)
        regions = []
        for i in range(len(data["text"])):
            if int(data["conf"][i]) > 0 and data["text"][i].strip():
                regions.append({
                    "text": data["text"][i],
                    "confidence": int(data["conf"][i]) / 100.0,
                    "x": data["left"][i], "y": data["top"][i],
                    "w": data["width"][i], "h": data["height"][i],
                })
        elapsed = (time.perf_counter() - t0) * 1000
        return Prediction(task=TaskType.OCR, text=text.strip(),
                          text_regions=regions, inference_time_ms=elapsed)

    def postprocess(self, output: Any, original_shape: tuple[int, ...]) -> Prediction:
        return Prediction(task=TaskType.OCR)


@ModelRegistry.register("easyocr", task="ocr", family="easyocr")
class EasyOCRWrapper(BaseModel):
    """EasyOCR wrapper. Install: pip install easyocr"""

    @property
    def task_type(self) -> TaskType:
        return TaskType.OCR

    def build_model(self, config: Config) -> nn.Module:
        try:
            import easyocr
        except ImportError:
            raise ImportError("Install easyocr: pip install easyocr")
        langs = config.get("model.languages", ["en"])
        gpu = config.get("inference.device", "auto") != "cpu"
        self._reader = easyocr.Reader(langs, gpu=gpu)
        return _DummyModule()

    def preprocess(self, image: np.ndarray) -> torch.Tensor:
        return torch.empty(0)

    @torch.inference_mode()
    def predict(self, image: np.ndarray) -> Prediction:
        t0 = time.perf_counter()
        results = self._reader.readtext(image)
        full_text_parts = []
        regions = []
        for bbox, text, conf in results:
            full_text_parts.append(text)
            flat = [coord for pt in bbox for coord in pt]
            regions.append({
                "text": text, "confidence": float(conf),
                "bbox": flat,
            })
        elapsed = (time.perf_counter() - t0) * 1000
        return Prediction(task=TaskType.OCR, text=" ".join(full_text_parts),
                          text_regions=regions, inference_time_ms=elapsed)

    def postprocess(self, output: Any, original_shape: tuple[int, ...]) -> Prediction:
        return Prediction(task=TaskType.OCR)
