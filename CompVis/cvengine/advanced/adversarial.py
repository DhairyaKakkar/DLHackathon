"""Adversarial robustness testing with FGSM and PGD attacks.

Use this to evaluate how resilient your model is to adversarial perturbations—
useful for research papers, security-aware demos, and competition edge cases.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import torch
import torch.nn as nn
from torchvision import transforms

from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class AdversarialTester:
    """Generate adversarial examples and measure model robustness.

    Supports FGSM (fast, single-step) and PGD (stronger, multi-step).
    """

    def __init__(self, model: nn.Module, device: torch.device | str = "cpu",
                 normalize: transforms.Normalize | None = None):
        self.model = model
        self.device = torch.device(device) if isinstance(device, str) else device
        self.model.to(self.device)
        self.model.eval()
        self._normalize = normalize

    def fgsm_attack(self, images: torch.Tensor, labels: torch.Tensor,
                    epsilon: float = 0.03) -> torch.Tensor:
        """Fast Gradient Sign Method — single-step attack."""
        images = images.clone().detach().to(self.device).requires_grad_(True)
        labels = labels.to(self.device)
        output = self.model(images)
        loss = nn.functional.cross_entropy(output, labels)
        loss.backward()
        perturbed = images + epsilon * images.grad.sign()
        return perturbed.clamp(0, 1).detach()

    def pgd_attack(self, images: torch.Tensor, labels: torch.Tensor,
                   epsilon: float = 0.03, alpha: float = 0.007,
                   steps: int = 10) -> torch.Tensor:
        """Projected Gradient Descent — iterative multi-step attack."""
        original = images.clone().detach().to(self.device)
        perturbed = original.clone().requires_grad_(True)
        labels = labels.to(self.device)

        for _ in range(steps):
            output = self.model(perturbed)
            loss = nn.functional.cross_entropy(output, labels)
            loss.backward()
            with torch.no_grad():
                perturbed = perturbed + alpha * perturbed.grad.sign()
                # Project back to epsilon-ball
                delta = torch.clamp(perturbed - original, -epsilon, epsilon)
                perturbed = torch.clamp(original + delta, 0, 1).requires_grad_(True)

        return perturbed.detach()

    @torch.no_grad()
    def evaluate_robustness(
        self,
        images: torch.Tensor,
        labels: torch.Tensor,
        epsilons: list[float] | None = None,
    ) -> dict[str, Any]:
        """Run FGSM and PGD at multiple epsilon values, report accuracy drop.

        Returns a dict with clean accuracy and per-epsilon attack results.
        """
        if epsilons is None:
            epsilons = [0.0, 0.01, 0.03, 0.05, 0.1]

        images = images.to(self.device)
        labels = labels.to(self.device)

        # Clean accuracy
        clean_pred = self.model(images).argmax(dim=1)
        clean_acc = float((clean_pred == labels).float().mean())

        results: dict[str, Any] = {"clean_accuracy": clean_acc, "attacks": []}

        for eps in epsilons:
            if eps == 0:
                continue
            # Need gradients for attacks
            fgsm_imgs = self.fgsm_attack(images, labels, eps)
            fgsm_pred = self.model(fgsm_imgs).argmax(dim=1)
            fgsm_acc = float((fgsm_pred == labels).float().mean())

            pgd_imgs = self.pgd_attack(images, labels, eps)
            pgd_pred = self.model(pgd_imgs).argmax(dim=1)
            pgd_acc = float((pgd_pred == labels).float().mean())

            results["attacks"].append({
                "epsilon": eps,
                "fgsm_accuracy": fgsm_acc,
                "pgd_accuracy": pgd_acc,
                "fgsm_drop": clean_acc - fgsm_acc,
                "pgd_drop": clean_acc - pgd_acc,
            })
            log.info("eps=%.3f | FGSM acc=%.3f | PGD acc=%.3f", eps, fgsm_acc, pgd_acc)

        return results
