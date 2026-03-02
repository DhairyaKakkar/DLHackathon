"""
CVEngine - A production-ready, modular Computer Vision framework.

Supports classification, detection, segmentation, OCR, video streaming,
and real-time inference with config-driven model switching.
"""

import os as _os

# Must be set BEFORE torch is imported — enables CPU fallback for ops
# not yet implemented on Apple MPS (e.g. torchvision::nms).
_os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

__version__ = "0.1.0"

from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry, TaskRegistry
from cvengine.inference.pipeline import InferencePipeline

__all__ = ["Config", "ModelRegistry", "TaskRegistry", "InferencePipeline"]
