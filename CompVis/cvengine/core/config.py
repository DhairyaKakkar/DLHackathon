"""Config-driven model and pipeline switching via YAML files."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml


_DEFAULTS: dict[str, Any] = {
    "task": "classification",
    "model": {"name": "resnet50", "pretrained": True, "num_classes": 1000, "weights": None},
    "data": {
        "image_size": 224,
        "batch_size": 32,
        "num_workers": 4,
        "pin_memory": True,
        "train_split": 0.8,
        "augmentation": "default",
    },
    "training": {
        "epochs": 10,
        "lr": 1e-3,
        "optimizer": "adam",
        "scheduler": "cosine",
        "weight_decay": 1e-4,
        "early_stopping_patience": 5,
        "mixed_precision": True,
        "gradient_clip": 1.0,
    },
    "inference": {
        "device": "auto",
        "batch_size": 1,
        "confidence_threshold": 0.5,
        "nms_threshold": 0.45,
    },
    "logging": {
        "level": "INFO",
        "log_dir": "runs",
        "use_wandb": False,
        "use_tensorboard": True,
    },
}


class Config:
    """Hierarchical config with YAML loading, dot-access, and CLI overrides."""

    def __init__(self, data: dict[str, Any] | None = None):
        self._data = copy.deepcopy(_DEFAULTS)
        if data:
            self._deep_update(self._data, data)

    # --- factories -----------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return cls(raw)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Config:
        return cls(d)

    # --- access --------------------------------------------------------------

    def get(self, dotted_key: str, default: Any = None) -> Any:
        keys = dotted_key.split(".")
        node = self._data
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def set(self, dotted_key: str, value: Any) -> None:
        keys = dotted_key.split(".")
        node = self._data
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        node[keys[-1]] = value

    def merge(self, overrides: dict[str, Any]) -> Config:
        new = Config(self._data)
        new._deep_update(new._data, overrides)
        return new

    def merge_cli(self, args: list[str]) -> Config:
        """Parse key=value CLI overrides like 'training.lr=0.001'."""
        overrides: dict[str, Any] = {}
        for arg in args:
            if "=" not in arg:
                continue
            key, val = arg.split("=", 1)
            val = self._auto_cast(val)
            parts = key.split(".")
            d = overrides
            for p in parts[:-1]:
                d = d.setdefault(p, {})
            d[parts[-1]] = val
        return self.merge(overrides)

    def to_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def save(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self._data, f, default_flow_style=False, sort_keys=False)

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _deep_update(base: dict, updates: dict) -> dict:
        for k, v in updates.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                Config._deep_update(base[k], v)
            else:
                base[k] = v
        return base

    @staticmethod
    def _auto_cast(val: str) -> Any:
        if val.lower() in ("true", "yes"):
            return True
        if val.lower() in ("false", "no"):
            return False
        if val.lower() == "none":
            return None
        try:
            return int(val)
        except ValueError:
            pass
        try:
            return float(val)
        except ValueError:
            pass
        return val

    def __repr__(self) -> str:
        return f"Config({yaml.dump(self._data, default_flow_style=True).strip()})"
