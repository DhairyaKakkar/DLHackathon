#!/usr/bin/env python3
"""Quick classification demo — run pretrained ResNet/EfficientNet on any image.

Usage:
    python examples/classification_demo.py --image cat.jpg
    python examples/classification_demo.py --image cat.jpg --model efficientnet_b0
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvengine.inference.pipeline import InferencePipeline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--model", type=str, default="resnet50")
    args = parser.parse_args()

    pipe = InferencePipeline.from_config(config_dict={
        "model": {"name": args.model, "pretrained": True},
        "inference": {"device": "auto"},
    })

    pred = pipe(args.image)
    print(f"\nPrediction: {pred.class_name} ({pred.confidence:.2%})")
    print("Top-5:")
    for entry in (pred.top_k or []):
        print(f"  {entry['class_name']:>30s}  {entry['confidence']:.4f}")
    print(f"\nInference time: {pred.inference_time_ms:.1f} ms")


if __name__ == "__main__":
    main()
