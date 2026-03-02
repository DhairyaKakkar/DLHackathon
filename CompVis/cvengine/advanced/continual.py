"""Online continual learning with Elastic Weight Consolidation (EWC).

Use this when your model needs to learn new classes without forgetting old ones—
common in streaming, production, and competition scenarios.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class ContinualLearner:
    """EWC-based continual learning wrapper.

    Usage::

        cl = ContinualLearner(model, ewc_lambda=1000)
        # Train on task A
        cl.train_task(train_loader_a, epochs=5)
        cl.register_task()  # snapshot Fisher info
        # Train on task B — old knowledge preserved
        cl.train_task(train_loader_b, epochs=5)
    """

    def __init__(self, model: nn.Module, device: torch.device | str = "cpu",
                 lr: float = 1e-3, ewc_lambda: float = 400.0):
        self.model = model
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        self.lr = lr
        self.ewc_lambda = ewc_lambda
        self._fisher: dict[str, torch.Tensor] = {}
        self._old_params: dict[str, torch.Tensor] = {}
        self._tasks_registered = 0

    def register_task(self, dataloader: DataLoader | None = None) -> None:
        """Snapshot current parameters and compute Fisher information matrix.

        Call this after training on each task.
        """
        self._old_params = {n: p.clone().detach() for n, p in self.model.named_parameters() if p.requires_grad}

        if dataloader is not None:
            self._fisher = self._compute_fisher(dataloader)
        else:
            # Uniform Fisher if no data provided
            self._fisher = {n: torch.ones_like(p) for n, p in self.model.named_parameters() if p.requires_grad}

        self._tasks_registered += 1
        log.info("Registered task %d — Fisher info computed for %d parameters",
                 self._tasks_registered, len(self._fisher))

    def train_task(self, dataloader: DataLoader, epochs: int = 5,
                   criterion: nn.Module | None = None) -> list[float]:
        """Train the model on a new task with EWC regularization."""
        self.model.train()
        criterion = criterion or nn.CrossEntropyLoss()
        optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, self.model.parameters()),
                                     lr=self.lr)
        losses = []
        for epoch in range(epochs):
            epoch_loss = 0.0
            n = 0
            for inputs, targets in dataloader:
                inputs, targets = inputs.to(self.device), targets.to(self.device)
                optimizer.zero_grad()
                output = self.model(inputs)
                loss = criterion(output, targets)
                # Add EWC penalty
                if self._fisher:
                    loss = loss + self._ewc_penalty()
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * inputs.size(0)
                n += inputs.size(0)
            avg = epoch_loss / max(n, 1)
            losses.append(avg)
            log.info("Task %d | Epoch %d/%d | loss=%.4f",
                     self._tasks_registered + 1, epoch + 1, epochs, avg)
        return losses

    def _ewc_penalty(self) -> torch.Tensor:
        penalty = torch.tensor(0.0, device=self.device)
        for name, param in self.model.named_parameters():
            if name in self._fisher:
                penalty += (self._fisher[name] * (param - self._old_params[name]).pow(2)).sum()
        return self.ewc_lambda * penalty / 2

    @torch.no_grad()
    def _compute_fisher(self, dataloader: DataLoader) -> dict[str, torch.Tensor]:
        fisher: dict[str, torch.Tensor] = {n: torch.zeros_like(p)
                                            for n, p in self.model.named_parameters() if p.requires_grad}
        self.model.eval()
        criterion = nn.CrossEntropyLoss()
        n_samples = 0
        for inputs, targets in dataloader:
            inputs, targets = inputs.to(self.device), targets.to(self.device)
            self.model.zero_grad()
            output = self.model(inputs)
            loss = criterion(output, targets)
            loss.backward()
            for name, param in self.model.named_parameters():
                if param.grad is not None and name in fisher:
                    fisher[name] += param.grad.pow(2) * inputs.size(0)
            n_samples += inputs.size(0)
        for name in fisher:
            fisher[name] /= max(n_samples, 1)
        return fisher
