#!/usr/bin/env python3
"""Real-time webcam inference with any CVEngine model.

Usage:
    python examples/webcam_demo.py
    python examples/webcam_demo.py --model yolov8n --confidence 0.4
"""

import os
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # must be before torch import

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvengine.inference.pipeline import InferencePipeline
from cvengine.inference.stream import StreamingInference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default="yolov8n")
    parser.add_argument("--confidence", type=float, default=0.5)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--frame-skip", type=int, default=0)
    args = parser.parse_args()

    pipe = InferencePipeline.from_config(config_dict={
        "model": {"name": args.model},
        "inference": {"device": args.device, "confidence_threshold": args.confidence},
    })

    streamer = StreamingInference(
        pipeline=pipe,
        display=True,
        frame_skip=args.frame_skip,
    )

    print(f"Starting webcam inference with {args.model} — press 'q' to quit")
    results = streamer.run_on_webcam(device=args.camera)
    print(f"Done: {len(results)} frames processed at avg {streamer.avg_fps:.1f} FPS")


if __name__ == "__main__":
    main()
