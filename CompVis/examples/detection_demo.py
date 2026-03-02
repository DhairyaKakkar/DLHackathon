#!/usr/bin/env python3
"""Object detection demo with YOLOv8.

Usage:
    python examples/detection_demo.py --image street.jpg
    python examples/detection_demo.py --image street.jpg --model yolov8s --display
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
    parser.add_argument("--model", type=str, default="yolov8n")
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--display", action="store_true")
    args = parser.parse_args()

    pipe = InferencePipeline.from_config(config_dict={
        "model": {"name": args.model},
        "inference": {"device": "auto", "confidence_threshold": args.confidence},
    })

    pred = pipe(args.image)
    print(f"\nDetected {len(pred.boxes or [])} objects in {pred.inference_time_ms:.1f} ms:")
    for box in (pred.boxes or []):
        print(f"  {box.class_name:>15s}  conf={box.confidence:.2f}  "
              f"bbox=[{box.x1:.0f},{box.y1:.0f},{box.x2:.0f},{box.y2:.0f}]")

    if args.display:
        image = load_image(args.image, color="rgb")
        vis = draw_predictions(image, pred)
        cv2.imshow("Detection", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
        cv2.waitKey(0)
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
