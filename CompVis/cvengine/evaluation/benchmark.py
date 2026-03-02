"""Auto model benchmarking: latency, throughput, memory, accuracy comparison."""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import torch

from cvengine.core.config import Config
from cvengine.inference.pipeline import InferencePipeline
from cvengine.utils.logging import get_logger

log = get_logger(__name__)


@dataclass
class BenchmarkResult:
    model_name: str
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_fps: float
    peak_memory_mb: float
    param_count: int
    extra: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model_name,
            "avg_ms": round(self.avg_latency_ms, 2),
            "p50_ms": round(self.p50_latency_ms, 2),
            "p95_ms": round(self.p95_latency_ms, 2),
            "p99_ms": round(self.p99_latency_ms, 2),
            "fps": round(self.throughput_fps, 1),
            "memory_mb": round(self.peak_memory_mb, 1),
            "params": self.param_count,
            **self.extra,
        }


class ModelBenchmark:
    """Compare multiple models on latency, throughput, and memory."""

    def __init__(self, image_size: tuple[int, int] = (640, 480),
                 warmup_runs: int = 5, bench_runs: int = 50):
        self.image_size = image_size
        self.warmup = warmup_runs
        self.bench = bench_runs

    def run(self, configs: list[dict[str, Any] | str]) -> list[BenchmarkResult]:
        results = []
        for cfg_src in configs:
            if isinstance(cfg_src, str):
                cfg = Config.from_yaml(cfg_src)
            else:
                cfg = Config.from_dict(cfg_src)

            name = cfg.get("model.name", "unknown")
            log.info("Benchmarking: %s", name)

            pipe = InferencePipeline.from_config(config_dict=cfg.to_dict())
            dummy = np.random.randint(0, 255, (*self.image_size, 3), dtype=np.uint8)

            # Warmup
            for _ in range(self.warmup):
                pipe(dummy)

            # Measure peak memory before
            if torch.cuda.is_available():
                torch.cuda.reset_peak_memory_stats()

            latencies = []
            for _ in range(self.bench):
                t0 = time.perf_counter()
                pipe(dummy)
                latencies.append((time.perf_counter() - t0) * 1000)

            lat = np.array(latencies)
            peak_mem = 0.0
            if torch.cuda.is_available():
                peak_mem = torch.cuda.max_memory_allocated() / 1024 / 1024

            params = pipe.model.parameter_count()["total"]
            results.append(BenchmarkResult(
                model_name=name,
                avg_latency_ms=float(lat.mean()),
                p50_latency_ms=float(np.percentile(lat, 50)),
                p95_latency_ms=float(np.percentile(lat, 95)),
                p99_latency_ms=float(np.percentile(lat, 99)),
                throughput_fps=1000.0 / float(lat.mean()) if lat.mean() > 0 else 0,
                peak_memory_mb=peak_mem,
                param_count=params,
                extra={},
            ))

            # Cleanup
            del pipe
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        self._print_table(results)
        return results

    @staticmethod
    def _print_table(results: list[BenchmarkResult]) -> None:
        header = f"{'Model':<25} {'Avg(ms)':>8} {'P95(ms)':>8} {'FPS':>7} {'Mem(MB)':>8} {'Params':>12}"
        log.info("\n%s\n%s", header, "-" * len(header))
        for r in results:
            log.info("%-25s %8.1f %8.1f %7.1f %8.1f %12s",
                     r.model_name, r.avg_latency_ms, r.p95_latency_ms,
                     r.throughput_fps, r.peak_memory_mb, f"{r.param_count:,}")
