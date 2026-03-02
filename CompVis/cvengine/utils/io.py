"""Image I/O helpers — load from path / URL / bytes, save, batch-load."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import cv2
import numpy as np

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def load_image(source: str | Path | bytes, color: str = "rgb") -> np.ndarray:
    """Load an image from a file path or raw bytes.

    Args:
        source: file path or raw bytes
        color: 'rgb' or 'bgr'
    """
    if isinstance(source, (str, Path)):
        img = cv2.imread(str(source))
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {source}")
    elif isinstance(source, bytes):
        arr = np.frombuffer(source, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Cannot decode image from bytes")
    else:
        raise TypeError(f"Unsupported source type: {type(source)}")

    if color == "rgb":
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def save_image(image: np.ndarray, path: str | Path, bgr: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = image if bgr else cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(path), out)


def load_images_from_dir(directory: str | Path,
                         extensions: Sequence[str] | None = None,
                         color: str = "rgb") -> list[tuple[Path, np.ndarray]]:
    exts = set(extensions) if extensions else _IMAGE_EXTS
    results = []
    for p in sorted(Path(directory).iterdir()):
        if p.suffix.lower() in exts:
            results.append((p, load_image(p, color=color)))
    return results
