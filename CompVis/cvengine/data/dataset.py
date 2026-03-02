"""Reusable dataset classes for classification / detection / segmentation.

Supports:
  - ImageFolder layout (class-per-directory)
  - CSV-driven datasets (path, label columns)
  - Custom dataset via subclass
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import cv2
import numpy as np
import pandas as pd
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset, random_split

from cvengine.data.transforms import get_transforms


class ImageFolderDataset(Dataset):
    """Standard image-folder layout: root/<class_name>/*.jpg"""

    def __init__(self, root: str | Path, transform: Callable | None = None,
                 extensions: set[str] | None = None):
        self.root = Path(root)
        self.transform = transform
        exts = extensions or {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        self.classes = sorted([d.name for d in self.root.iterdir() if d.is_dir()])
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}

        self.samples: list[tuple[Path, int]] = []
        for cls_name in self.classes:
            cls_dir = self.root / cls_name
            for p in sorted(cls_dir.iterdir()):
                if p.suffix.lower() in exts:
                    self.samples.append((p, self.class_to_idx[cls_name]))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor | Any, int]:
        path, label = self.samples[idx]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label


class CSVDataset(Dataset):
    """CSV-based dataset: columns for image_path and label."""

    def __init__(self, csv_path: str | Path, image_col: str = "image_path",
                 label_col: str = "label", root: str | Path | None = None,
                 transform: Callable | None = None):
        self.df = pd.read_csv(csv_path)
        self.root = Path(root) if root else Path(".")
        self.image_col = image_col
        self.label_col = label_col
        self.transform = transform

        labels = sorted(self.df[label_col].unique())
        self.class_to_idx = {l: i for i, l in enumerate(labels)}
        self.classes = labels

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor | Any, int]:
        row = self.df.iloc[idx]
        path = self.root / row[self.image_col]
        label = self.class_to_idx[row[self.label_col]]
        image = Image.open(path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label


class SegmentationDataset(Dataset):
    """Image + mask pairs for segmentation tasks.

    Layout:
        images_dir/<name>.jpg
        masks_dir/<name>.png  (single-channel class IDs)
    """

    def __init__(self, images_dir: str | Path, masks_dir: str | Path,
                 image_size: int = 256, transform: Callable | None = None):
        self.images_dir = Path(images_dir)
        self.masks_dir = Path(masks_dir)
        self.image_size = image_size
        self.transform = transform
        self.samples = sorted([p.stem for p in self.images_dir.iterdir()
                               if p.suffix.lower() in {".jpg", ".jpeg", ".png"}])

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        name = self.samples[idx]
        # Try common extensions
        img_path = None
        for ext in [".jpg", ".jpeg", ".png"]:
            candidate = self.images_dir / f"{name}{ext}"
            if candidate.exists():
                img_path = candidate
                break
        mask_path = self.masks_dir / f"{name}.png"

        image = cv2.imread(str(img_path))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (self.image_size, self.image_size))
        mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        mask = cv2.resize(mask, (self.image_size, self.image_size),
                          interpolation=cv2.INTER_NEAREST)

        image_tensor = torch.from_numpy(image).permute(2, 0, 1).float() / 255.0
        mask_tensor = torch.from_numpy(mask).long()
        return image_tensor, mask_tensor


def create_dataloaders(
    dataset: Dataset,
    batch_size: int = 32,
    train_split: float = 0.8,
    num_workers: int = 4,
    pin_memory: bool = True,
) -> dict[str, DataLoader]:
    """Split a dataset into train/val and return DataLoaders."""
    n = len(dataset)  # type: ignore[arg-type]
    n_train = int(n * train_split)
    n_val = n - n_train
    train_ds, val_ds = random_split(dataset, [n_train, n_val])
    return {
        "train": DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                            num_workers=num_workers, pin_memory=pin_memory),
        "val": DataLoader(val_ds, batch_size=batch_size, shuffle=False,
                          num_workers=num_workers, pin_memory=pin_memory),
    }
