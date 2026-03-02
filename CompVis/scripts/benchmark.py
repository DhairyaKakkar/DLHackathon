#!/usr/bin/env python3
"""Auto-benchmark multiple models and print a comparison table.

Usage:
    python scripts/benchmark.py
    python scripts/benchmark.py --models resnet18 resnet50 efficientnet_b0
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvengine.evaluation.benchmark import ModelBenchmark
import cvengine.models  # noqa: F401


def main():
    parser = argparse.ArgumentParser(description="CVEngine Benchmark")
    parser.add_argument("--models", nargs="+",
                        default=["resnet18", "resnet50", "efficientnet_b0", "efficientnet_b2"])
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--size", type=int, nargs=2, default=[480, 640])
    parser.add_argument("--output", type=str, default="benchmark_results.json")
    args = parser.parse_args()

    configs = [{"model": {"name": m, "pretrained": True}} for m in args.models]

    bench = ModelBenchmark(
        image_size=tuple(args.size),
        warmup_runs=args.warmup,
        bench_runs=args.runs,
    )
    results = bench.run(configs)

    out = [r.to_dict() for r in results]
    with open(args.output, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
