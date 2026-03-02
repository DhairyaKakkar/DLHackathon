"""Generic training loop for any PyTorch model with mixed precision, gradient
clipping, scheduling, callbacks, and metric logging."""

from __future__ import annotations

from typing import Any

import torch
import torch.nn as nn
from torch.cuda.amp import GradScaler
from torch.utils.data import DataLoader

from cvengine.core.config import Config
from cvengine.training.callbacks import Callback
from cvengine.utils.logging import MetricLogger, get_logger

log = get_logger(__name__)


class Trainer:
    """Config-driven training loop.

    Example::

        trainer = Trainer(config, model.model, loaders, criterion)
        trainer.fit()
    """

    def __init__(
        self,
        config: Config,
        model: nn.Module,
        loaders: dict[str, DataLoader],
        criterion: nn.Module,
        callbacks: list[Callback] | None = None,
        metric_logger: MetricLogger | None = None,
    ):
        self.config = config
        self.model = model
        self.loaders = loaders
        self.criterion = criterion
        self.callbacks = callbacks or []
        self.metric_logger = metric_logger or MetricLogger(
            log_dir=config.get("logging.log_dir", "runs"),
            use_tensorboard=config.get("logging.use_tensorboard", False),
            use_wandb=config.get("logging.use_wandb", False),
        )

        self.device = self._resolve_device(config.get("inference.device", "auto"))
        self.model.to(self.device)

        self.optimizer = self._build_optimizer()
        self.scheduler = self._build_scheduler()
        self.epochs = config.get("training.epochs", 10)
        self.grad_clip = config.get("training.gradient_clip", 1.0)
        self._use_amp = config.get("training.mixed_precision", True) and self.device.type == "cuda"
        self._scaler = GradScaler(enabled=self._use_amp)

    def fit(self) -> dict[str, list[float]]:
        history: dict[str, list[float]] = {"train_loss": [], "val_loss": []}
        for epoch in range(1, self.epochs + 1):
            train_loss = self._train_epoch()
            val_loss = self._val_epoch() if "val" in self.loaders else 0.0
            lr = self.optimizer.param_groups[0]["lr"]

            history["train_loss"].append(train_loss)
            history["val_loss"].append(val_loss)

            logs = {"train_loss": train_loss, "val_loss": val_loss, "lr": lr}
            self.metric_logger.log(logs, step=epoch)
            log.info("Epoch %d/%d | train_loss=%.4f | val_loss=%.4f | lr=%.6f",
                     epoch, self.epochs, train_loss, val_loss, lr)

            if self.scheduler is not None:
                self.scheduler.step()

            for cb in self.callbacks:
                cb.on_epoch_end(epoch, logs, self.model)
                if cb.should_stop:
                    log.info("Training stopped by callback")
                    self.metric_logger.close()
                    return history

        for cb in self.callbacks:
            cb.on_train_end({"history": history})
        self.metric_logger.close()
        return history

    # --- internal -------------------------------------------------------------

    def _train_epoch(self) -> float:
        self.model.train()
        total_loss = 0.0
        n = 0
        for batch in self.loaders["train"]:
            inputs, targets = self._to_device(batch)
            self.optimizer.zero_grad()
            with torch.autocast(device_type=self.device.type, enabled=self._use_amp):
                outputs = self.model(inputs)
                loss = self.criterion(outputs, targets)
            self._scaler.scale(loss).backward()
            if self.grad_clip:
                self._scaler.unscale_(self.optimizer)
                nn.utils.clip_grad_norm_(self.model.parameters(), self.grad_clip)
            self._scaler.step(self.optimizer)
            self._scaler.update()
            total_loss += loss.item() * inputs.size(0)
            n += inputs.size(0)
        return total_loss / max(n, 1)

    @torch.inference_mode()
    def _val_epoch(self) -> float:
        self.model.eval()
        total_loss = 0.0
        n = 0
        for batch in self.loaders["val"]:
            inputs, targets = self._to_device(batch)
            with torch.autocast(device_type=self.device.type, enabled=self._use_amp):
                outputs = self.model(inputs)
                loss = self.criterion(outputs, targets)
            total_loss += loss.item() * inputs.size(0)
            n += inputs.size(0)
        return total_loss / max(n, 1)

    def _to_device(self, batch: tuple) -> tuple:
        return tuple(b.to(self.device) if isinstance(b, torch.Tensor) else b for b in batch)

    def _build_optimizer(self) -> torch.optim.Optimizer:
        name = self.config.get("training.optimizer", "adam").lower()
        lr = self.config.get("training.lr", 1e-3)
        wd = self.config.get("training.weight_decay", 1e-4)
        params = filter(lambda p: p.requires_grad, self.model.parameters())
        if name == "sgd":
            return torch.optim.SGD(params, lr=lr, momentum=0.9, weight_decay=wd)
        if name == "adamw":
            return torch.optim.AdamW(params, lr=lr, weight_decay=wd)
        return torch.optim.Adam(params, lr=lr, weight_decay=wd)

    def _build_scheduler(self) -> torch.optim.lr_scheduler.LRScheduler | None:
        name = self.config.get("training.scheduler", "cosine").lower()
        if name == "cosine":
            return torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=self.epochs)
        if name == "step":
            return torch.optim.lr_scheduler.StepLR(self.optimizer, step_size=max(self.epochs // 3, 1))
        if name == "plateau":
            return torch.optim.lr_scheduler.ReduceLROnPlateau(self.optimizer, patience=3)
        return None

    @staticmethod
    def _resolve_device(device: str) -> torch.device:
        if device == "auto":
            if torch.cuda.is_available():
                return torch.device("cuda")
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return torch.device("mps")
            return torch.device("cpu")
        return torch.device(device)
