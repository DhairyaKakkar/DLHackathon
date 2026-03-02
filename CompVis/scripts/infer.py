#!/usr/bin/env python3
"""Run inference on a single image, directory, or video.

Usage:
    python scripts/infer.py --config configs/detection.yaml --input photo.jpg
    python scripts/infer.py --config configs/detection.yaml --input images/
    python scripts/infer.py --config configs/detection.yaml --input video.mp4
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvengine.core.config import Config
from cvengine.inference.pipeline import InferencePipeline
from cvengine.inference.batch import batch_inference
from cvengine.inference.stream import StreamingInference
import cvengine.models  # noqa: F401


def main():
    parser = argparse.ArgumentParser(description="CVEngine Inference")
    parser.add_argument("--config", type=str, default="configs/default.yaml")
    parser.add_argument("--input", type=str, required=True)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--display", action="store_true")
    args, extra = parser.parse_known_args()

    cfg = Config.from_yaml(args.config).merge_cli(extra)
    pipe = InferencePipeline.from_config(config_dict=cfg.to_dict())

    src = Path(args.input)

    if src.is_dir():
        batch_inference(pipe, src, output_json=args.output or "batch_results.json")

    elif src.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv", ".webm"}:
        streamer = StreamingInference(pipe, display=args.display)
        results = streamer.run_on_video(str(src))
        print(f"Processed {len(results)} frames, avg {streamer.avg_fps:.1f} FPS")

    else:
        pred = pipe(str(src))
        import json
        print(json.dumps(pred.to_dict(), indent=2, default=str))

        if args.display:
            from cvengine.utils.io import load_image
            from cvengine.utils.visualization import draw_predictions
            import cv2
            image = load_image(str(src), color="rgb")
            vis = draw_predictions(image, pred)
            cv2.imshow("Prediction", cv2.cvtColor(vis, cv2.COLOR_RGB2BGR))
            cv2.waitKey(0)
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
