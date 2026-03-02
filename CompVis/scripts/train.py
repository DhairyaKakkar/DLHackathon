#!/usr/bin/env python3
"""Train a model using CVEngine.

Usage:
    python scripts/train.py --config configs/classification.yaml --data data/cats_dogs
    python scripts/train.py --config configs/classification.yaml training.lr=0.0001
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch.nn as nn

from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.data.dataset import ImageFolderDataset, create_dataloaders
from cvengine.data.transforms import get_transforms
from cvengine.training.trainer import Trainer
from cvengine.training.callbacks import EarlyStopping, ModelCheckpoint, LRLogger
import cvengine.models  # noqa: F401


def main():
    parser = argparse.ArgumentParser(description="CVEngine Training")
    parser.add_argument("--config", type=str, default="configs/classification.yaml")
    parser.add_argument("--data", type=str, required=True, help="Path to image folder dataset")
    parser.add_argument("--output", type=str, default="checkpoints")
    args, extra = parser.parse_known_args()

    cfg = Config.from_yaml(args.config).merge_cli(extra)

    # Dataset
    train_transform = get_transforms("train", cfg.get("data.image_size"), cfg.get("data.augmentation"))
    val_transform = get_transforms("val", cfg.get("data.image_size"))

    train_ds = ImageFolderDataset(args.data, transform=train_transform)
    print(f"Dataset: {len(train_ds)} images, {len(train_ds.classes)} classes")
    print(f"Classes: {train_ds.classes}")

    # Override num_classes
    cfg.set("model.num_classes", len(train_ds.classes))
    cfg.set("model.labels", train_ds.classes)

    loaders = create_dataloaders(
        train_ds,
        batch_size=cfg.get("data.batch_size"),
        train_split=cfg.get("data.train_split"),
        num_workers=cfg.get("data.num_workers"),
    )

    # Model
    model_cls = ModelRegistry.get(cfg.get("model.name"))
    wrapper = model_cls(cfg)
    wrapper.train_mode()

    # Train
    trainer = Trainer(
        config=cfg,
        model=wrapper.model,
        loaders=loaders,
        criterion=nn.CrossEntropyLoss(),
        callbacks=[
            EarlyStopping(patience=cfg.get("training.early_stopping_patience")),
            ModelCheckpoint(save_dir=args.output),
            LRLogger(),
        ],
    )
    history = trainer.fit()
    print(f"\nTraining complete. Best val_loss: {min(history['val_loss']):.4f}")
    print(f"Checkpoints saved to: {args.output}")


if __name__ == "__main__":
    main()
