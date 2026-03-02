"""Streamlit dashboard for CVEngine — interactive demo in < 60 seconds.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import streamlit as st

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cvengine.core.config import Config
from cvengine.core.registry import ModelRegistry
from cvengine.inference.pipeline import InferencePipeline
from cvengine.utils.io import load_image
from cvengine.utils.visualization import draw_predictions
import cvengine.models  # noqa: F401

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="CVEngine Dashboard", page_icon="🔬", layout="wide")
st.title("🔬 CVEngine — Computer Vision Dashboard")

# ---------------------------------------------------------------------------
# Sidebar: model selection
# ---------------------------------------------------------------------------
st.sidebar.header("Model Configuration")
available = ModelRegistry.list_keys()
model_name = st.sidebar.selectbox("Model", available, index=available.index("resnet50") if "resnet50" in available else 0)
confidence = st.sidebar.slider("Confidence threshold", 0.0, 1.0, 0.5, 0.05)
device = st.sidebar.selectbox("Device", ["auto", "cpu", "cuda", "mps"])


@st.cache_resource
def get_pipeline(name: str, conf: float, dev: str) -> InferencePipeline:
    cfg = Config.from_dict({
        "model": {"name": name, "pretrained": True},
        "inference": {"device": dev, "confidence_threshold": conf},
    })
    return InferencePipeline.from_config(config_dict=cfg.to_dict())


pipe = get_pipeline(model_name, confidence, device)

st.sidebar.success(f"Model loaded: **{model_name}** on `{pipe.model.device}`")
params = pipe.model.parameter_count()
st.sidebar.info(f"Parameters: {params['total']:,} ({params['trainable']:,} trainable)")

# ---------------------------------------------------------------------------
# Main area: file upload + inference
# ---------------------------------------------------------------------------
tab_img, tab_batch, tab_webcam = st.tabs(["Single Image", "Batch Upload", "Webcam"])

with tab_img:
    uploaded = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "bmp", "webp"])
    if uploaded:
        raw = uploaded.read()
        image = load_image(raw, color="rgb")
        pred = pipe(image)

        col1, col2 = st.columns(2)
        with col1:
            st.image(image, caption="Input", use_container_width=True)
        with col2:
            vis = draw_predictions(image, pred)
            st.image(vis, caption="Prediction", use_container_width=True)

        st.subheader("Results")
        st.json(pred.to_dict())
        st.metric("Inference time", f"{pred.inference_time_ms:.1f} ms")

with tab_batch:
    files = st.file_uploader("Upload images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)
    if files:
        images = [load_image(f.read(), color="rgb") for f in files]
        preds = pipe.predict_batch(images)

        for img, pred, f in zip(images, preds, files):
            with st.expander(f.name):
                c1, c2 = st.columns(2)
                c1.image(img, caption="Input", use_container_width=True)
                vis = draw_predictions(img, pred)
                c2.image(vis, caption="Prediction", use_container_width=True)
                st.json(pred.to_dict())

with tab_webcam:
    st.info("Webcam inference requires running locally. Use `python examples/webcam_demo.py` for real-time inference.")
    if st.button("Take snapshot (if webcam available)"):
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pred = pipe(frame_rgb)
            vis = draw_predictions(frame_rgb, pred)
            st.image(vis, caption="Webcam snapshot", use_container_width=True)
            st.json(pred.to_dict())
        else:
            st.error("Could not access webcam")
