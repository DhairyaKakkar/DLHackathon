"""Centralized logging with optional TensorBoard / W&B integration."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any


_CONFIGURED = False


def setup_logging(level: str = "INFO", log_dir: str | None = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(Path(log_dir) / "cvengine.log"))

    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO),
                        format=fmt, handlers=handlers)
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)


class MetricLogger:
    """Lightweight metric tracker that optionally pushes to TensorBoard / W&B."""

    def __init__(self, log_dir: str = "runs", use_tensorboard: bool = False,
                 use_wandb: bool = False, project: str = "cvengine"):
        self._log = get_logger("metrics")
        self._step = 0
        self._history: list[dict[str, Any]] = []
        self._tb_writer = None
        self._wandb_run = None

        if use_tensorboard:
            try:
                from torch.utils.tensorboard import SummaryWriter
                self._tb_writer = SummaryWriter(log_dir=log_dir)
                self._log.info("TensorBoard logging enabled -> %s", log_dir)
            except ImportError:
                self._log.warning("tensorboard not installed, skipping")

        if use_wandb:
            try:
                import wandb
                self._wandb_run = wandb.init(project=project, reinit=True)
                self._log.info("W&B logging enabled -> %s", project)
            except ImportError:
                self._log.warning("wandb not installed, skipping")

    def log(self, metrics: dict[str, float], step: int | None = None) -> None:
        step = step if step is not None else self._step
        self._history.append({"step": step, **metrics})
        self._step = step + 1

        if self._tb_writer:
            for k, v in metrics.items():
                self._tb_writer.add_scalar(k, v, global_step=step)

        if self._wandb_run:
            import wandb
            wandb.log(metrics, step=step)

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)

    def close(self) -> None:
        if self._tb_writer:
            self._tb_writer.close()
        if self._wandb_run:
            import wandb
            wandb.finish()
