"""Batch inference over directories, CSV manifests, or lists of paths."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from cvengine.core.types import BatchPrediction, Prediction
from cvengine.inference.pipeline import InferencePipeline
from cvengine.utils.io import load_images_from_dir
from cvengine.utils.logging import get_logger

log = get_logger(__name__)


def batch_inference(
    pipeline: InferencePipeline,
    source: str | Path | list[str | Path],
    output_json: str | Path | None = None,
) -> BatchPrediction:
    """Run inference on a directory of images or a list of paths.

    Returns a BatchPrediction containing all results plus total wall time.
    """
    t0 = time.perf_counter()

    if isinstance(source, (str, Path)) and Path(source).is_dir():
        pairs = load_images_from_dir(source)
        paths = [p for p, _ in pairs]
        images = [img for _, img in pairs]
    else:
        if isinstance(source, (str, Path)):
            source = [source]
        paths = [Path(s) for s in source]
        images = []
        for s in source:
            from cvengine.utils.io import load_image
            images.append(load_image(s, color="rgb"))

    predictions: list[Prediction] = []
    for i, (path, img) in enumerate(zip(paths, images)):
        pred = pipeline(img)
        pred.metadata["source"] = str(path)
        predictions.append(pred)
        if (i + 1) % 50 == 0:
            log.info("Processed %d / %d", i + 1, len(images))

    total_ms = (time.perf_counter() - t0) * 1000
    batch = BatchPrediction(predictions=predictions, total_time_ms=total_ms)
    log.info("Batch done: %d images in %.1f ms (%.1f ms/img)",
             len(predictions), total_ms, total_ms / max(len(predictions), 1))

    if output_json:
        import json
        out = [p.to_dict() for p in predictions]
        Path(output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(output_json, "w") as f:
            json.dump(out, f, indent=2, default=str)
        log.info("Results saved -> %s", output_json)

    return batch
