"""Asynchronous frame stream with producer/consumer pattern.

Decouples capture from inference so that slow models don't stall the capture
loop and fast models can skip stale frames.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable, Iterator

import numpy as np

from cvengine.data.video import VideoCapture, WebcamCapture
from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class FrameStream:
    """Thread-safe frame stream with optional frame-skip for real-time use."""

    def __init__(self, source: VideoCapture | WebcamCapture | Iterator[np.ndarray],
                 buffer_size: int = 8, skip_stale: bool = True):
        self._source = source
        self._buffer: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=buffer_size)
        self._skip_stale = skip_stale
        self._running = False
        self._thread: threading.Thread | None = None
        self._frame_count = 0
        self._dropped = 0

    def start(self) -> FrameStream:
        self._running = True
        self._thread = threading.Thread(target=self._producer, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3)
        log.info("Stream stopped — %d frames captured, %d dropped", self._frame_count, self._dropped)

    def _producer(self) -> None:
        for frame in self._source:
            if not self._running:
                break
            try:
                self._buffer.put_nowait(frame)
                self._frame_count += 1
            except queue.Full:
                if self._skip_stale:
                    try:
                        self._buffer.get_nowait()
                        self._dropped += 1
                    except queue.Empty:
                        pass
                    self._buffer.put_nowait(frame)
                    self._frame_count += 1
        self._buffer.put(None)  # sentinel

    def __iter__(self) -> Iterator[np.ndarray]:
        while True:
            frame = self._buffer.get()
            if frame is None:
                break
            yield frame

    def __enter__(self) -> FrameStream:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    @property
    def stats(self) -> dict[str, int]:
        return {"frames": self._frame_count, "dropped": self._dropped,
                "buffer_size": self._buffer.qsize()}


def run_streaming_inference(
    source: VideoCapture | WebcamCapture,
    predict_fn: Callable[[np.ndarray], dict],
    on_result: Callable[[np.ndarray, dict], None] | None = None,
    max_fps: float = 30.0,
) -> None:
    """Convenience: run inference on a stream, calling on_result per frame."""
    min_interval = 1.0 / max_fps
    with FrameStream(source) as stream:
        for frame in stream:
            t0 = time.perf_counter()
            result = predict_fn(frame)
            if on_result:
                on_result(frame, result)
            elapsed = time.perf_counter() - t0
            sleep = min_interval - elapsed
            if sleep > 0:
                time.sleep(sleep)
