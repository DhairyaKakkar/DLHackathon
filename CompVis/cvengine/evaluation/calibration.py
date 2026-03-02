"""Confidence calibration: ECE, reliability diagrams, temperature scaling."""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader


def expected_calibration_error(
    confidences: np.ndarray,
    predictions: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 15,
) -> float:
    """Compute Expected Calibration Error (ECE).

    Lower is better — measures how well confidence matches actual accuracy.
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (confidences > lo) & (confidences <= hi)
        if mask.sum() == 0:
            continue
        bin_acc = (predictions[mask] == labels[mask]).mean()
        bin_conf = confidences[mask].mean()
        ece += mask.sum() / len(confidences) * abs(bin_acc - bin_conf)
    return float(ece)


def reliability_diagram(
    confidences: np.ndarray,
    predictions: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 15,
) -> dict[str, Any]:
    """Return data for a reliability diagram (accuracy vs confidence per bin)."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bins_data = []
    for i in range(n_bins):
        lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (confidences > lo) & (confidences <= hi)
        count = int(mask.sum())
        if count == 0:
            bins_data.append({"bin_lo": lo, "bin_hi": hi, "accuracy": 0, "confidence": 0, "count": 0})
            continue
        acc = float((predictions[mask] == labels[mask]).mean())
        conf = float(confidences[mask].mean())
        bins_data.append({"bin_lo": lo, "bin_hi": hi, "accuracy": acc, "confidence": conf, "count": count})
    return {"bins": bins_data, "ece": expected_calibration_error(confidences, predictions, labels, n_bins)}


class TemperatureScaling(nn.Module):
    """Post-hoc temperature scaling to calibrate a classifier.

    Usage:
        ts = TemperatureScaling()
        ts.fit(model, val_loader, device)
        calibrated_logits = ts(raw_logits)
    """

    def __init__(self):
        super().__init__()
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, logits: torch.Tensor) -> torch.Tensor:
        return logits / self.temperature

    @torch.no_grad()
    def fit(self, model: nn.Module, loader: DataLoader, device: torch.device,
            max_iter: int = 50, lr: float = 0.01) -> float:
        """Optimize temperature on a validation set.

        Returns the final temperature value.
        """
        model.eval()
        all_logits = []
        all_labels = []
        for inputs, labels in loader:
            inputs = inputs.to(device)
            logits = model(inputs)
            all_logits.append(logits.cpu())
            all_labels.append(labels)
        logits_cat = torch.cat(all_logits)
        labels_cat = torch.cat(all_labels)

        criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)

        def closure():
            optimizer.zero_grad()
            loss = criterion(self(logits_cat), labels_cat)
            loss.backward()
            return loss

        optimizer.step(closure)
        return float(self.temperature.item())
