"""Training callbacks: early stopping, checkpointing, LR logging."""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any

import torch

from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class Callback(abc.ABC):
    def on_epoch_end(self, epoch: int, logs: dict[str, float], model: torch.nn.Module) -> None:
        pass

    def on_train_end(self, logs: dict[str, Any]) -> None:
        pass

    @property
    def should_stop(self) -> bool:
        return False


class EarlyStopping(Callback):
    def __init__(self, patience: int = 5, monitor: str = "val_loss", mode: str = "min"):
        self.patience = patience
        self.monitor = monitor
        self._best = float("inf") if mode == "min" else float("-inf")
        self._compare = (lambda a, b: a < b) if mode == "min" else (lambda a, b: a > b)
        self._wait = 0
        self._stop = False

    @property
    def should_stop(self) -> bool:
        return self._stop

    def on_epoch_end(self, epoch: int, logs: dict[str, float], model: torch.nn.Module) -> None:
        val = logs.get(self.monitor)
        if val is None:
            return
        if self._compare(val, self._best):
            self._best = val
            self._wait = 0
        else:
            self._wait += 1
            if self._wait >= self.patience:
                log.info("Early stopping triggered at epoch %d", epoch)
                self._stop = True


class ModelCheckpoint(Callback):
    def __init__(self, save_dir: str = "checkpoints", monitor: str = "val_loss",
                 mode: str = "min", save_best_only: bool = True):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.monitor = monitor
        self._best = float("inf") if mode == "min" else float("-inf")
        self._compare = (lambda a, b: a < b) if mode == "min" else (lambda a, b: a > b)
        self.save_best_only = save_best_only

    def on_epoch_end(self, epoch: int, logs: dict[str, float], model: torch.nn.Module) -> None:
        val = logs.get(self.monitor)
        path = self.save_dir / f"epoch_{epoch:03d}.pt"
        if self.save_best_only:
            if val is not None and self._compare(val, self._best):
                self._best = val
                best_path = self.save_dir / "best.pt"
                torch.save(model.state_dict(), best_path)
                log.info("Saved best model -> %s (%.4f)", best_path, val)
        else:
            torch.save(model.state_dict(), path)


class LRLogger(Callback):
    def on_epoch_end(self, epoch: int, logs: dict[str, float], model: torch.nn.Module) -> None:
        lr = logs.get("lr")
        if lr is not None:
            log.info("Epoch %d | LR = %.6f", epoch, lr)
