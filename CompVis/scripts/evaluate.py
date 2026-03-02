#!/usr/bin/env python3
"""Evaluate a trained model on a test dataset.

Usage:
    python scripts/evaluate.py --config configs/classification.yaml \
        --data data/test --weights checkpoints/best.pt
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.data.dataset import ImageFolderDataset
from cvengine.data.transforms import get_transforms
from cvengine.evaluation.metrics import ClassificationEvaluator
from cvengine.inference.pipeline import InferencePipeline
from cvengine.utils.io import load_image
import cvengine.models  # noqa: F401


def main():
    parser = argparse.ArgumentParser(description="CVEngine Evaluation")
    parser.add_argument("--config", type=str, default="configs/classification.yaml")
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--weights", type=str, default=None)
    parser.add_argument("--output", type=str, default="eval_results.json")
    args, extra = parser.parse_known_args()

    cfg = Config.from_yaml(args.config).merge_cli(extra)
    if args.weights:
        cfg.set("model.weights", args.weights)

    dataset = ImageFolderDataset(args.data, transform=None)
    cfg.set("model.num_classes", len(dataset.classes))
    cfg.set("model.labels", dataset.classes)

    pipe = InferencePipeline.from_config(config_dict=cfg.to_dict())
    if args.weights:
        pipe.model.load(args.weights)

    evaluator = ClassificationEvaluator()
    for i, (path, label) in enumerate(dataset.samples):
        image = load_image(path, color="rgb")
        pred = pipe(image)
        evaluator.update(pred, label)
        if (i + 1) % 100 == 0:
            print(f"Evaluated {i + 1}/{len(dataset)}")

    results = evaluator.compute()
    print(f"\nAccuracy: {results['accuracy']:.4f}")
    print(f"Macro F1: {results['macro_f1']:.4f}")

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
