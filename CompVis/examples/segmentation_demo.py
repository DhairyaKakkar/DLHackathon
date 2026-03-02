#!/usr/bin/env python3
"""Semantic segmentation demo with DeepLabV3 or U-Net.

Usage:
    python examples/segmentation_demo.py --image room.jpg
    python examples/segmentation_demo.py --image room.jpg --model deeplabv3_resnet101 --display
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2
from cvengine.inference.pipeline import InferencePipeline
from cvengine.utils.io import load_image
from cvengine.utils.visualization import draw_predictions


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=str, required=True)
    parser.add_argument("--model", type=str, default="deeplabv3_resnet50")
    parser.add_argument("--display", action="store_true")
    args = parser.parse_args()

    pipe = InferencePipeline.from_config(config_dict={
        "model": {"name": args.model, "pretrained": True},
        "inference": {"device": "auto"},
    })

    pred = pipe(args.image)
    mask = pred.mask
    if mask is not None:
        unique_classes = set(mask.flatten().tolist())
        print(f"\nSegmentation complete in {pred.inference_time_ms:.1f} ms")
        print(f"Mask shape: {mask.shape}")
        print(f"Unique classes: {unique_classes}")

    if args.display and mask is not None:
        image = load_image(args.image, color="rgb")
        vis = draw_predictions(image, pred)
        cv2.imshow("Segmentation", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
