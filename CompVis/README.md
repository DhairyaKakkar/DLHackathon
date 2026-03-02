# CVEngine

**A production-ready, modular Computer Vision framework built with PyTorch.**

CVEngine eliminates the 4-5 hours of boilerplate you write at the start of every CV project. It provides a unified interface for classification, detection, segmentation, and OCR — with config-driven model switching, streaming inference, a FastAPI backend, and a Streamlit dashboard out of the box.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        USER ENTRY POINTS                         │
│  InferencePipeline  │  Trainer  │  FastAPI  │  Streamlit  │ CLI  │
└──────────┬───────────────┬──────────┬───────────┬────────────────┘
           │               │          │           │
┌──────────▼───────────────▼──────────▼───────────▼────────────────┐
│                         CORE LAYER                               │
│  Config (YAML)  │  Registry (plugins)  │  BaseModel (abstract)   │
│  Types (Prediction, BoundingBox, TaskType)                       │
└──────────┬───────────────┬──────────────────────┬────────────────┘
           │               │                      │
┌──────────▼───┐  ┌───────▼────────┐  ┌──────────▼───────────────┐
│   MODELS     │  │   DATA LAYER   │  │     INFERENCE LAYER      │
│ Classification│  │ ImageFolder    │  │ Pipeline (single image)  │
│ Detection    │  │ CSV Dataset    │  │ Batch (directory)        │
│ Segmentation │  │ Segmentation   │  │ Streaming (video/webcam) │
│ OCR          │  │ Video/Webcam   │  │ Ensemble (multi-model)   │
│              │  │ FrameStream    │  │                          │
└──────────────┘  └────────────────┘  └──────────────────────────┘
           │               │                      │
┌──────────▼───────────────▼──────────────────────▼────────────────┐
│                      EVALUATION & ADVANCED                       │
│ Metrics │ Calibration │ Benchmark │ Drift │ Adversarial │ Edge   │
│ Continual Learning │ Ensemble │ ONNX Export │ Quantization       │
└──────────────────────────────────────────────────────────────────┘
```

### Why each module exists

| Module | Purpose | When you need it |
|--------|---------|-----------------|
| `core/config.py` | YAML-driven config with dot-access and CLI overrides | Every project — swap models by changing one line |
| `core/registry.py` | Plugin system — `@ModelRegistry.register("name")` | Adding new model architectures |
| `core/base.py` | Abstract contract: `build_model`, `preprocess`, `postprocess` | Ensures every model has the same interface |
| `core/types.py` | `Prediction`, `BoundingBox`, `TaskType` dataclasses | Unified output format across all tasks |
| `models/` | Pretrained wrappers (ResNet, EfficientNet, YOLO, U-Net, DeepLab, SAM, OCR) | Instant access to SOTA models |
| `data/` | Dataset loaders, augmentation presets, video/webcam capture | Loading any data source in 2 lines |
| `training/` | Generic training loop with AMP, callbacks, scheduling | Fine-tuning on custom datasets |
| `inference/` | Pipeline, batch, streaming, ensemble | Running predictions |
| `evaluation/` | Metrics, calibration, benchmarking | Measuring quality and speed |
| `advanced/` | Continual learning, adversarial testing, drift detection, edge export | Research and production hardening |

---

## Quick Start

```bash
# Install
pip install -e ".[dev,api,dashboard]"

# Classify an image
python examples/classification_demo.py --image photo.jpg

# Detect objects
python examples/detection_demo.py --image street.jpg --model yolov8n --display

# Segment an image
python examples/segmentation_demo.py --image room.jpg --display

# Real-time webcam detection
python examples/webcam_demo.py --model yolov8n

# Launch API server
make api

# Launch Streamlit dashboard
make dashboard

# Run benchmarks
make benchmark

# Run tests
make test
```

### 3-Line Inference

```python
from cvengine.inference.pipeline import InferencePipeline

pipe = InferencePipeline.from_config("configs/detection.yaml")
result = pipe("photo.jpg")
print(result.to_dict())
```

### Config-Driven Model Switching

```python
# Switch from ResNet to EfficientNet by changing one field
pipe = InferencePipeline.from_config(config_dict={
    "model": {"name": "efficientnet_b0", "pretrained": True},
})
```

### Training

```bash
python scripts/train.py --config configs/classification.yaml --data ./my_dataset/
```

### REST API

```bash
uvicorn api.main:app --port 8000

# POST an image
curl -X POST http://localhost:8000/predict -F "file=@photo.jpg"

# Hot-swap model
curl -X POST http://localhost:8000/switch-model \
  -H "Content-Type: application/json" \
  -d '{"model_name": "yolov8n"}'
```

---

## Folder Structure

```
CompVis/
├── configs/              # YAML configs for each task
│   ├── default.yaml
│   ├── classification.yaml
│   ├── detection.yaml
│   ├── segmentation.yaml
│   └── ocr.yaml
├── cvengine/             # Core framework
│   ├── core/             # Config, Registry, BaseModel, Types
│   ├── models/           # Model wrappers (classification, detection, segmentation, ocr)
│   ├── data/             # Datasets, transforms, video, streaming
│   ├── training/         # Trainer, callbacks
│   ├── inference/        # Pipeline, batch, streaming, ensemble
│   ├── evaluation/       # Metrics, calibration, benchmarking
│   ├── advanced/         # Continual learning, adversarial, drift, edge
│   └── utils/            # Logging, visualization, I/O
├── api/                  # FastAPI REST backend
├── dashboard/            # Streamlit interactive dashboard
├── scripts/              # CLI tools (train, evaluate, infer, benchmark)
├── examples/             # Ready-to-run demos
├── tests/                # pytest test suite
├── Dockerfile
├── Makefile
├── setup.py
└── requirements.txt
```

---

## Registered Models

| Name | Task | Pretrained | Notes |
|------|------|-----------|-------|
| `resnet18/34/50/101/152` | Classification | Yes | ImageNet weights |
| `efficientnet_b0..b4` | Classification | Yes | ImageNet weights |
| `custom_classifier` | Classification | No | 4-layer CNN for small datasets |
| `yolov8n/s/m/l/x` | Detection | Yes | Requires `ultralytics` |
| `custom_detector` | Detection | No | Mini SSD-style detector |
| `unet` | Segmentation | No | Classic U-Net |
| `deeplabv3_resnet50/101` | Segmentation | Yes | COCO weights |
| `sam_vit_b/l/h` | Segmentation | Yes | Requires `segment-anything` |
| `tesseract` | OCR | N/A | Requires system Tesseract |
| `easyocr` | OCR | Yes | Requires `easyocr` |

---

## How to Use in Different Contexts

### Hackathon (0 to demo in 30 minutes)
1. Pick a config: `configs/detection.yaml`
2. Run `python examples/detection_demo.py --image input.jpg --display`
3. Launch `make dashboard` for the interactive Streamlit UI
4. Deploy with `make docker-build && make docker-run`

### Research Competition
1. Use the training pipeline with heavy augmentation
2. Ensemble multiple models for higher accuracy
3. Use `ModelBenchmark` to find the speed/accuracy sweet spot
4. Use calibration module to report ECE in your writeup

### Coursework
1. Extend `BaseModel` to implement a novel architecture
2. Use the evaluation metrics module for your report
3. Compare models with `scripts/benchmark.py`

### Startup MVP
1. Build on the FastAPI backend (`api/main.py`)
2. Add authentication middleware
3. Deploy via Docker to any cloud provider
4. Hot-swap models in production via `/switch-model`

---

## Extending the Framework

### Add a new model

```python
from cvengine.core.base import BaseModel
from cvengine.core.registry import ModelRegistry
from cvengine.core.types import TaskType

@ModelRegistry.register("my_model", task="classification")
class MyModel(BaseModel):
    @property
    def task_type(self):
        return TaskType.CLASSIFICATION

    def build_model(self, config):
        ...  # Return nn.Module

    def preprocess(self, image):
        ...  # Return batched tensor

    def postprocess(self, output, original_shape):
        ...  # Return Prediction
```

The model is now available everywhere: pipeline, API, dashboard, CLI.

### Add a new task type

1. Add to `TaskType` enum in `core/types.py`
2. Add fields to `Prediction` dataclass
3. Create model wrappers in a new `models/` subdirectory
4. Register with `@ModelRegistry.register`

---

## Research Extension Ideas

This framework can be the foundation for novel research:

1. **Adaptive Model Selection** — Use drift detection to automatically switch models when input distribution changes. Publishable as "Online Model Selection for Non-Stationary Visual Streams."

2. **Efficient Ensemble Distillation** — Train a student from the ensemble module's combined predictions. Paper: "Self-Distilled Ensembles for Resource-Constrained CV."

3. **Continual Few-Shot Learning** — Combine the continual learning module with meta-learning for class-incremental few-shot detection.

4. **Calibration-Aware Active Learning** — Use ECE and confidence distributions to select the most informative samples for labeling.

5. **Cross-Task Transfer** — Use segmentation features as priors for detection, leveraging the shared `BaseModel` interface.

---

## License

MIT
