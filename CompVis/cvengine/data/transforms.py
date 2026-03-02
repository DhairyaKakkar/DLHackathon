"""Augmentation presets for train / val / test splits."""

from __future__ import annotations

from torchvision import transforms


def get_transforms(
    split: str = "train",
    image_size: int = 224,
    augmentation: str = "default",
) -> transforms.Compose:
    """Return a torchvision transform pipeline.

    Args:
        split: 'train', 'val', or 'test'.
        image_size: target spatial size.
        augmentation: 'default', 'heavy', 'light', or 'none'.
    """
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])

    if split != "train" or augmentation == "none":
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.ToTensor(),
            normalize,
        ])

    if augmentation == "light":
        return transforms.Compose([
            transforms.Resize((image_size, image_size)),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            normalize,
        ])

    if augmentation == "heavy":
        return transforms.Compose([
            transforms.RandomResizedCrop(image_size, scale=(0.6, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(30),
            transforms.ColorJitter(brightness=0.4, contrast=0.4, saturation=0.4, hue=0.1),
            transforms.RandomGrayscale(p=0.1),
            transforms.GaussianBlur(kernel_size=3),
            transforms.ToTensor(),
            normalize,
            transforms.RandomErasing(p=0.25),
        ])

    # default
    return transforms.Compose([
        transforms.RandomResizedCrop(image_size, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        normalize,
    ])
