"""
PINN Brain Tumor Predictor
==========================

Single integration point for the user's trained PINN model.

HOW TO WIRE IN YOUR MODEL:
  1. Drop your trained model file into /app/backend/models/
     Supported file names (priority order):
       - pinn_model.pth   (PyTorch state_dict)   <-- recommended
       - pinn_model.pt    (TorchScript)
       - pinn_model.h5    (Keras / TF)
       - pinn_model.onnx  (ONNX)
  2. Open the `_load_model()` function below.
  3. Un-comment the PyTorch/TF reference block that matches your framework
     and tweak the model class / preprocessing to match your training code.
  4. Done — the API endpoint /api/predict will use it automatically.

If no model file is found, the predictor returns a mocked but realistic
response (demo mode) so the full UX is testable.
"""
from __future__ import annotations

import io
import os
import random
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List

from PIL import Image

MODELS_DIR = Path(__file__).parent
TUMOR_CLASSES: List[str] = ["no_tumor", "glioma", "meningioma", "pituitary"]

_SUPPORTED_FILES = [
    "pinn_model.pth",
    "pinn_model.pt",
    "pinn_model.h5",
    "pinn_model.onnx",
]


@dataclass
class PredictionResult:
    tumor_detected: bool
    tumor_type: str          # one of TUMOR_CLASSES
    confidence: float        # 0.0 - 1.0
    class_probabilities: dict
    demo_mode: bool
    model_file: str | None

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
_model = None
_model_path: Path | None = None


def _find_model_file() -> Path | None:
    for name in _SUPPORTED_FILES:
        p = MODELS_DIR / name
        if p.exists():
            return p
    return None


def _load_model():
    """
    Replace the body of this function with your own loader when you drop
    your trained model file into /app/backend/models/.

    ----- PyTorch reference (uncomment & adapt) -----
    import torch
    from .your_arch import PINNClassifier   # <-- your model class
    model = PINNClassifier(num_classes=len(TUMOR_CLASSES))
    model.load_state_dict(torch.load(_model_path, map_location="cpu"))
    model.eval()
    return model

    ----- TensorFlow / Keras reference -----
    from tensorflow.keras.models import load_model
    return load_model(str(_model_path))
    """
    return None  # demo mode until user plugs their model in


def _ensure_loaded():
    global _model, _model_path
    if _model is not None:
        return
    _model_path = _find_model_file()
    if _model_path is None:
        return
    try:
        _model = _load_model()
    except Exception as exc:  # pragma: no cover
        print(f"[pinn_predictor] failed to load model: {exc}")
        _model = None


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------
def _preprocess(image_bytes: bytes) -> Image.Image:
    """Minimal preprocessing — adapt to match your training pipeline."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L")  # grayscale MRI
    img = img.resize((224, 224))
    return img


def _mock_prediction(image_bytes: bytes) -> PredictionResult:
    """
    Deterministic-ish mock that mimics real model output so the end-to-end
    UX can be demonstrated without a trained model.
    """
    seed = sum(image_bytes[:256]) if image_bytes else 0
    rng = random.Random(seed)

    probs = [rng.random() for _ in TUMOR_CLASSES]
    total = sum(probs)
    probs = [p / total for p in probs]
    top_idx = probs.index(max(probs))

    return PredictionResult(
        tumor_detected=TUMOR_CLASSES[top_idx] != "no_tumor",
        tumor_type=TUMOR_CLASSES[top_idx],
        confidence=round(probs[top_idx], 4),
        class_probabilities={c: round(p, 4) for c, p in zip(TUMOR_CLASSES, probs)},
        demo_mode=True,
        model_file=None,
    )


def predict(image_bytes: bytes) -> PredictionResult:
    """
    Public API used by the FastAPI route.

    When you plug your model in, replace the `return _mock_prediction(...)`
    line with real inference using `_model` and `_preprocess(image_bytes)`.
    """
    _ensure_loaded()

    if _model is None:
        return _mock_prediction(image_bytes)

    # ----- Real inference reference (adapt to your model) -----
    # import torch
    # from torchvision import transforms
    # img = _preprocess(image_bytes)
    # tensor = transforms.ToTensor()(img).unsqueeze(0)
    # with torch.no_grad():
    #     logits = _model(tensor)
    #     probs = torch.softmax(logits, dim=1).squeeze().tolist()
    # top_idx = int(max(range(len(probs)), key=lambda i: probs[i]))
    # return PredictionResult(
    #     tumor_detected=TUMOR_CLASSES[top_idx] != "no_tumor",
    #     tumor_type=TUMOR_CLASSES[top_idx],
    #     confidence=round(probs[top_idx], 4),
    #     class_probabilities={c: round(p, 4) for c, p in zip(TUMOR_CLASSES, probs)},
    #     demo_mode=False,
    #     model_file=_model_path.name if _model_path else None,
    # )

    # until the above is enabled we fall back to mock
    return _mock_prediction(image_bytes)


def model_status() -> dict:
    _ensure_loaded()
    return {
        "model_loaded": _model is not None,
        "model_file": _model_path.name if _model_path else None,
        "demo_mode": _model is None,
        "supported_files": _SUPPORTED_FILES,
        "classes": TUMOR_CLASSES,
    }
