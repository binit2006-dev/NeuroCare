"""
PINN Brain Tumor Predictor — wired to the user's trained checkpoint
(`pinn_model.pth`, originally `improved_all_improvements_s3_amp_seed0.pth`).

The checkpoint is a state_dict only, so the architecture below was rebuilt
from its tensor shapes: a 4-level U-Net encoder/decoder that predicts a tumor
density field `u`, Fisher-KPP physics terms (learned log_D, log_rho and a
Laplacian kernel), and a classifier over [GAP(encoder) 256 + 3 physics feats].

If your training code differs, adjust the CONFIG block or `PhysicsFeatures`.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

import numpy as np
from PIL import Image

MODELS_DIR = Path(__file__).parent
MODEL_FILE = MODELS_DIR / "pinn_model.pth"

# ---------------- CONFIG (match your training pipeline) ----------------
# Alphabetical ImageFolder order (glioma, meningioma, notumor, pituitary).
TUMOR_CLASSES: List[str] = ["glioma", "meningioma", "no_tumor", "pituitary"]
IMG_SIZE = 256
NORM_MEAN = [0.485, 0.456, 0.406]
NORM_STD = [0.229, 0.224, 0.225]
# -----------------------------------------------------------------------


@dataclass
class PredictionResult:
    tumor_detected: bool
    tumor_type: str
    confidence: float
    class_probabilities: dict
    demo_mode: bool
    model_file: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


_model = None
_load_error: Optional[str] = None


def _build_model():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    def block(i, o):
        return nn.Sequential(
            nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
            nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
        )

    def up(t, ref):
        return F.interpolate(t, size=ref.shape[-2:], mode="bilinear", align_corners=False)

    class BrainTumorPINN(nn.Module):
        def __init__(self, num_classes=4):
            super().__init__()
            self.log_D = nn.Parameter(torch.tensor(0.0))
            self.log_rho = nn.Parameter(torch.tensor(0.0))
            self.register_buffer("lap_kernel", torch.zeros(1, 1, 3, 3))
            self.block1, self.block2 = block(3, 32), block(32, 64)
            self.block3, self.block4 = block(64, 128), block(128, 256)
            self.up1 = nn.Conv2d(256, 64, 3, padding=1)
            self.up2 = nn.Conv2d(192, 32, 3, padding=1)
            self.up3 = nn.Conv2d(96, 32, 3, padding=1)
            self.out = nn.Conv2d(32, 1, 1)
            self.classifier = nn.Sequential(
                nn.Dropout(), nn.Linear(256 + 3, 128), nn.ReLU(), nn.Dropout(), nn.Linear(128, num_classes)
            )

        def physics_features(self, u):
            # Fisher-KPP: D * lap(u) + rho * u * (1 - u)
            lap = F.conv2d(u, self.lap_kernel, padding=1)
            res = self.log_D.exp() * lap + self.log_rho.exp() * u * (1 - u)
            b = u.shape[0]
            return torch.stack([u.view(b, -1).mean(1), lap.abs().view(b, -1).mean(1), res.abs().view(b, -1).mean(1)], 1)

        def forward(self, x):
            e1 = self.block1(x)
            e2 = self.block2(F.max_pool2d(e1, 2))
            e3 = self.block3(F.max_pool2d(e2, 2))
            e4 = self.block4(F.max_pool2d(e3, 2))
            d = torch.cat([F.relu(self.up1(up(e4, e3))), e3], 1)
            d = torch.cat([F.relu(self.up2(up(d, e2))), e2], 1)
            d = F.relu(self.up3(up(d, e1)))
            u = torch.sigmoid(self.out(d))
            feat = torch.cat([F.adaptive_avg_pool2d(e4, 1).flatten(1), self.physics_features(u)], 1)
            return self.classifier(feat)

    torch.set_num_threads(2)
    model = BrainTumorPINN(len(TUMOR_CLASSES))
    sd = torch.load(MODEL_FILE, map_location="cpu")
    if isinstance(sd, dict) and "model_state_dict" in sd:
        sd = sd["model_state_dict"]
    model.load_state_dict(sd)
    model.eval()
    return model


def _ensure_loaded():
    global _model, _load_error
    if _model is not None or _load_error is not None or not MODEL_FILE.exists():
        return
    try:
        _model = _build_model()
    except Exception as exc:
        _load_error = str(exc)
        print(f"[pinn_predictor] failed to load model: {exc}")


def _preprocess(image_bytes: bytes):
    import torch
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR)
    a = (np.asarray(img, dtype=np.float32) / 255.0 - NORM_MEAN) / NORM_STD
    return torch.from_numpy(a.astype(np.float32)).permute(2, 0, 1).unsqueeze(0)


def _mock_prediction(image_bytes: bytes) -> PredictionResult:
    import random
    rng = random.Random(sum(image_bytes[:256]))
    probs = [rng.random() for _ in TUMOR_CLASSES]
    probs = [p / sum(probs) for p in probs]
    top = probs.index(max(probs))
    return PredictionResult(
        tumor_detected=TUMOR_CLASSES[top] != "no_tumor",
        tumor_type=TUMOR_CLASSES[top],
        confidence=round(probs[top], 4),
        class_probabilities={c: round(p, 4) for c, p in zip(TUMOR_CLASSES, probs)},
        demo_mode=True,
        model_file=None,
    )


def predict(image_bytes: bytes) -> PredictionResult:
    _ensure_loaded()
    if _model is None:
        return _mock_prediction(image_bytes)
    import torch
    with torch.no_grad():
        probs = torch.softmax(_model(_preprocess(image_bytes)), dim=1).squeeze(0).tolist()
    top = max(range(len(probs)), key=lambda i: probs[i])
    return PredictionResult(
        tumor_detected=TUMOR_CLASSES[top] != "no_tumor",
        tumor_type=TUMOR_CLASSES[top],
        confidence=round(probs[top], 4),
        class_probabilities={c: round(p, 4) for c, p in zip(TUMOR_CLASSES, probs)},
        demo_mode=False,
        model_file=MODEL_FILE.name,
    )


def model_status() -> dict:
    _ensure_loaded()
    return {
        "model_loaded": _model is not None,
        "model_file": MODEL_FILE.name if _model is not None else None,
        "demo_mode": _model is None,
        "load_error": _load_error,
        "classes": TUMOR_CLASSES,
        "input_size": IMG_SIZE,
    }
