"""Global registries for models and tasks — the plugin backbone of CVEngine.

Usage:
    @ModelRegistry.register("resnet50")
    class ResNet50Wrapper(BaseModel):
        ...

    model_cls = ModelRegistry.get("resnet50")
"""

from __future__ import annotations

from typing import Any, Callable, Type


class _Registry:
    """Generic string -> class registry with metadata."""

    def __init__(self, name: str):
        self._name = name
        self._store: dict[str, dict[str, Any]] = {}

    def register(self, key: str, **meta: Any) -> Callable:
        def decorator(cls: Type) -> Type:
            self._store[key] = {"cls": cls, **meta}
            return cls
        return decorator

    def get(self, key: str) -> Type:
        if key not in self._store:
            available = ", ".join(sorted(self._store))
            raise KeyError(f"[{self._name}] '{key}' not found. Available: {available}")
        return self._store[key]["cls"]

    def get_meta(self, key: str) -> dict[str, Any]:
        return {k: v for k, v in self._store[key].items() if k != "cls"}

    def list_keys(self) -> list[str]:
        return sorted(self._store.keys())

    def __contains__(self, key: str) -> bool:
        return key in self._store

    def __repr__(self) -> str:
        return f"{self._name}Registry({self.list_keys()})"


ModelRegistry = _Registry("Model")
TaskRegistry = _Registry("Task")
