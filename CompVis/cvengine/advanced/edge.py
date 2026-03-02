"""Edge deployment optimizations: ONNX export, quantization, pruning."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import torch
import torch.nn as nn

from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class EdgeOptimizer:
    """Prepare models for edge deployment: quantize, prune, export to ONNX."""

    def __init__(self, model: nn.Module, device: str = "cpu"):
        self.model = model.to(device)
        self.device = device

    def quantize_dynamic(self) -> nn.Module:
        """Apply dynamic quantization (CPU-only, no calibration data needed)."""
        quantized = torch.quantization.quantize_dynamic(
            self.model, {nn.Linear, nn.Conv2d}, dtype=torch.qint8,
        )
        log.info("Dynamic quantization applied")
        return quantized

    def prune_unstructured(self, amount: float = 0.3) -> nn.Module:
        """Apply global unstructured L1 pruning."""
        import torch.nn.utils.prune as prune

        params_to_prune = []
        for name, module in self.model.named_modules():
            if isinstance(module, (nn.Conv2d, nn.Linear)):
                params_to_prune.append((module, "weight"))

        if params_to_prune:
            prune.global_unstructured(params_to_prune, pruning_method=prune.L1Unstructured, amount=amount)
            # Make pruning permanent
            for module, param_name in params_to_prune:
                prune.remove(module, param_name)
            log.info("Pruned %.0f%% of weights (L1 unstructured)", amount * 100)
        return self.model

    def export_onnx(self, output_path: str | Path, input_shape: tuple = (1, 3, 224, 224),
                    opset_version: int = 13) -> Path:
        """Export model to ONNX format."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        dummy = torch.randn(*input_shape).to(self.device)
        self.model.eval()
        torch.onnx.export(
            self.model, dummy, str(path),
            opset_version=opset_version,
            input_names=["input"],
            output_names=["output"],
            dynamic_axes={"input": {0: "batch"}, "output": {0: "batch"}},
        )
        log.info("ONNX exported -> %s (%.1f MB)", path, path.stat().st_size / 1024 / 1024)
        return path

    def export_torchscript(self, output_path: str | Path,
                           input_shape: tuple = (1, 3, 224, 224)) -> Path:
        """Export model to TorchScript for mobile / C++ inference."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.model.eval()
        dummy = torch.randn(*input_shape).to(self.device)
        traced = torch.jit.trace(self.model, dummy)
        traced.save(str(path))
        log.info("TorchScript exported -> %s", path)
        return path

    def profile(self, input_shape: tuple = (1, 3, 224, 224), runs: int = 100) -> dict[str, Any]:
        """Profile latency and parameter count."""
        import time
        self.model.eval()
        dummy = torch.randn(*input_shape).to(self.device)

        # Warmup
        for _ in range(10):
            self.model(dummy)

        times = []
        for _ in range(runs):
            t0 = time.perf_counter()
            self.model(dummy)
            times.append((time.perf_counter() - t0) * 1000)

        import numpy as np
        arr = np.array(times)
        total_params = sum(p.numel() for p in self.model.parameters())
        nonzero = sum((p != 0).sum().item() for p in self.model.parameters())
        return {
            "avg_ms": float(arr.mean()),
            "p95_ms": float(np.percentile(arr, 95)),
            "total_params": total_params,
            "nonzero_params": nonzero,
            "sparsity": 1.0 - nonzero / max(total_params, 1),
        }
