#!/usr/bin/env python3
"""Ensemble multiple classifiers for better accuracy.

Usage:
    python examples/ensemble_demo.py --image cat.jpg
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvengine.inference.pipeline import InferencePipeline
from cvengine.inference.ensemble import EnsembleModel
from cvengine.utils.io import load_image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str, required=True)
    args = parser.parse_args()

    models = ["resnet50", "efficientnet_b0", "resnet18"]
    pipes = []
    for m in models:
        pipe = InferencePipeline.from_config(config_dict={
            "model": {"name": m, "pretrained": True},
            "inference": {"device": "auto"},
        })
        pipes.append(pipe)

    ensemble = EnsembleModel(pipes, strategy="average")

    image = load_image(args.image, color="rgb")

    # Individual predictions
    for pipe, name in zip(pipes, models):
        pred = pipe(image)
        print(f"{name:>20s}: {pred.class_name} ({pred.confidence:.4f})")

    # Ensemble prediction
    ens_pred = ensemble.predict(image)
    print(f"\n{'ENSEMBLE':>20s}: {ens_pred.class_name} ({ens_pred.confidence:.4f})")
    print(f"Ensemble time: {ens_pred.inference_time_ms:.1f} ms")


if __name__ == "__main__":
    main()
