"""Video and webcam capture with frame-by-frame iteration."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from cvengine.utils.logging import get_logger

log = get_logger(__name__)


class VideoCapture:
    """Iterate over frames of a video file."""

    def __init__(self, path: str | Path, color: str = "rgb", max_frames: int = 0):
        self.path = str(path)
        self.color = color
        self.max_frames = max_frames
        self._cap: cv2.VideoCapture | None = None

    @property
    def fps(self) -> float:
        if self._cap is None:
            self._open()
        return self._cap.get(cv2.CAP_PROP_FPS)  # type: ignore[union-attr]

    @property
    def frame_count(self) -> int:
        if self._cap is None:
            self._open()
        return int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))  # type: ignore[union-attr]

    @property
    def resolution(self) -> tuple[int, int]:
        if self._cap is None:
            self._open()
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))  # type: ignore[union-attr]
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  # type: ignore[union-attr]
        return (w, h)

    def _open(self) -> None:
        self._cap = cv2.VideoCapture(self.path)
        if not self._cap.isOpened():
            raise IOError(f"Cannot open video: {self.path}")

    def __iter__(self) -> Iterator[np.ndarray]:
        self._open()
        count = 0
        while True:
            if self.max_frames and count >= self.max_frames:
                break
            ret, frame = self._cap.read()  # type: ignore[union-attr]
            if not ret:
                break
            if self.color == "rgb":
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            count += 1
            yield frame
        self._cap.release()  # type: ignore[union-attr]

    def __del__(self) -> None:
        if self._cap is not None and self._cap.isOpened():
            self._cap.release()


class WebcamCapture:
    """Real-time webcam frame iterator with optional display."""

    def __init__(self, device: int = 0, color: str = "rgb",
                 display: bool = False, window_name: str = "CVEngine Webcam"):
        self.device = device
        self.color = color
        self.display = display
        self.window_name = window_name

    def __iter__(self) -> Iterator[np.ndarray]:
        cap = cv2.VideoCapture(self.device)
        if not cap.isOpened():
            raise IOError(f"Cannot open webcam device {self.device}")
        log.info("Webcam %d opened — press 'q' to stop", self.device)
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                out = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if self.color == "rgb" else frame
                yield out
                if self.display:
                    show = frame if self.color == "bgr" else cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
                    cv2.imshow(self.window_name, show)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
        finally:
            cap.release()
            if self.display:
                cv2.destroyAllWindows()
