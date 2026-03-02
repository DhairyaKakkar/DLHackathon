"""Streaming inference with frame-by-frame adaptation and result callback."""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Callable

import cv2
import numpy as np

from cvengine.core.types import Prediction
from cvengine.data.video import VideoCapture, WebcamCapture
from cvengine.data.streaming import FrameStream
from cvengine.inference.pipeline import InferencePipeline
from cvengine.utils.logging import get_logger
from cvengine.utils.visualization import draw_predictions

log = get_logger(__name__)


class StreamingInference:
    """Real-time inference on video / webcam streams.

    Features:
        - FPS tracking with sliding window
        - Optional on-screen overlay
        - Per-frame callback for custom logic
        - Optional frame-skip for slow models
    """

    def __init__(self, pipeline: InferencePipeline, display: bool = False,
                 on_result: Callable[[np.ndarray, Prediction], None] | None = None,
                 frame_skip: int = 0):
        self.pipeline = pipeline
        self.display = display
        self.on_result = on_result
        self.frame_skip = frame_skip
        self._fps_window: deque[float] = deque(maxlen=30)

    @property
    def avg_fps(self) -> float:
        if not self._fps_window:
            return 0.0
        return len(self._fps_window) / sum(self._fps_window)

    def run_on_video(self, path: str, max_frames: int = 0) -> list[Prediction]:
        return self._run(VideoCapture(path, max_frames=max_frames))

    def run_on_webcam(self, device: int = 0) -> list[Prediction]:
        return self._run(WebcamCapture(device, display=False))

    def _run(self, source: VideoCapture | WebcamCapture) -> list[Prediction]:
        results: list[Prediction] = []
        frame_idx = 0
        with FrameStream(source) as stream:
            for frame in stream:
                if self.frame_skip and frame_idx % (self.frame_skip + 1) != 0:
                    frame_idx += 1
                    continue

                t0 = time.perf_counter()
                pred = self.pipeline(frame)
                dt = time.perf_counter() - t0
                self._fps_window.append(dt)
                results.append(pred)

                if self.on_result:
                    self.on_result(frame, pred)

                if self.display:
                    vis = draw_predictions(frame, pred)
                    vis = cv2.cvtColor(vis, cv2.COLOR_RGB2BGR)
                    fps_text = f"FPS: {self.avg_fps:.1f}"
                    cv2.putText(vis, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                                1, (0, 255, 0), 2)
                    cv2.imshow("CVEngine Stream", vis)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

                frame_idx += 1

        if self.display:
            cv2.destroyAllWindows()
        log.info("Stream complete: %d frames, avg %.1f FPS", len(results), self.avg_fps)
        return results
