"""
PINN Brain Tumor Predictor — uses the user's exact `ImprovedPINNCNN` class
(from improved_pinn_cnn.ipynb, variant "all_improvements": unet head, strided physics).
Checkpoint: models/pinn_model.pth (state_dict).
"""
from __future__ import annotations

import base64
import io
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional

import numpy as np
from PIL import Image, ImageFilter

MODELS_DIR = Path(__file__).parent
MODEL_FILE = MODELS_DIR / "pinn_model.pth"

# Training settings from the notebook (CLASS_NAMES / cnn_transform)
TUMOR_CLASSES: List[str] = ["glioma", "meningioma", "no_tumor", "pituitary"]
IMG_SIZE = 224
NORM_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
NORM_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
HEATMAP_MAX_SIDE = 512
HEATMAP_RGB = (232, 112, 84)  # warm coral glow


@dataclass
class PredictionResult:
    tumor_detected: bool
    tumor_type: str
    confidence: float
    class_probabilities: dict
    demo_mode: bool
    model_file: Optional[str]
    tumor_area_pct: Optional[float] = None
    heatmap: Optional[str] = field(default=None, repr=False)  # PNG data URL

    def to_dict(self) -> dict:
        return asdict(self)


_model = None
_load_error: Optional[str] = None


def _build_model():
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    def conv_block(cin, cout, p):
        return nn.Sequential(
            nn.Conv2d(cin, cout, 3, padding=1), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
            nn.Conv2d(cout, cout, 3, padding=1), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
            nn.MaxPool2d(2), nn.Dropout2d(p),
        )

    class ImprovedPINNCNN(nn.Module):
        def __init__(self, num_classes=4):
            super().__init__()
            self.block1 = conv_block(3, 32, 0.10)
            self.block2 = conv_block(32, 64, 0.15)
            self.block3 = conv_block(64, 128, 0.20)
            self.block4 = conv_block(128, 256, 0.25)
            self.up1 = nn.Conv2d(256, 64, 3, padding=1)
            self.up2 = nn.Conv2d(64 + 128, 32, 3, padding=1)
            self.up3 = nn.Conv2d(32 + 64, 32, 3, padding=1)
            self.out = nn.Conv2d(32, 1, 1)
            self.log_D = nn.Parameter(torch.tensor(-3.0))
            self.log_rho = nn.Parameter(torch.tensor(0.0))
            self.classifier = nn.Sequential(
                nn.Dropout(0.40), nn.Linear(256 + 3, 128), nn.ReLU(inplace=True),
                nn.Dropout(0.30), nn.Linear(128, num_classes),
            )
            lap = torch.tensor([[0., 1., 0.], [1., -4., 1.], [0., 1., 0.]]).view(1, 1, 3, 3)
            self.register_buffer("lap_kernel", lap)

        def forward(self, x):
            f1 = self.block1(x); f2 = self.block2(f1); f3 = self.block3(f2); f4 = self.block4(f3)
            h = F.interpolate(F.relu(self.up1(f4)), scale_factor=2, mode="bilinear", align_corners=False)
            h = F.interpolate(F.relu(self.up2(torch.cat([h, f3], 1))), scale_factor=2, mode="bilinear", align_corners=False)
            h = F.relu(self.up3(torch.cat([h, f2], 1)))
            u = torch.sigmoid(self.out(h))
            pooled = F.adaptive_avg_pool2d(f4, 1).flatten(1)
            u_stats = torch.stack([u.mean((1, 2, 3)), u.amax((1, 2, 3)), (u > 0.5).float().mean((1, 2, 3))], dim=1)
            return self.classifier(torch.cat([pooled, u_stats], dim=1)), u

    torch.set_num_threads(2)
    model = ImprovedPINNCNN(len(TUMOR_CLASSES))
    model.load_state_dict(torch.load(MODEL_FILE, map_location="cpu", weights_only=True))
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


def _preprocess(img: Image.Image):
    import torch
    a = np.asarray(img.resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR), dtype=np.float32) / 255.0
    a = (a - NORM_MEAN) / NORM_STD
    return torch.from_numpy(a).permute(2, 0, 1).unsqueeze(0)


def _heatmap_data_url(u: np.ndarray, size: tuple) -> str:
    w, h = size
    scale = min(1.0, HEATMAP_MAX_SIDE / max(w, h))
    out = (max(1, int(w * scale)), max(1, int(h * scale)))
    u = np.clip((u - 0.2) / 0.8, 0, 1)  # suppress faint background activation
    alpha = Image.fromarray((u ** 0.8 * 230).astype(np.uint8), "L").resize(out, Image.BICUBIC)
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=max(2, out[0] // 80)))
    rgba = Image.new("RGBA", out, HEATMAP_RGB + (0,))
    rgba.putalpha(alpha)
    buf = io.BytesIO()
    rgba.save(buf, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _mock_prediction(image_bytes: bytes) -> PredictionResult:
    import random
    rng = random.Random(sum(image_bytes[:256]))
    probs = [rng.random() for _ in TUMOR_CLASSES]
    probs = [p / sum(probs) for p in probs]
    top = probs.index(max(probs))
    return PredictionResult(
        tumor_detected=TUMOR_CLASSES[top] != "no_tumor", tumor_type=TUMOR_CLASSES[top],
        confidence=round(probs[top], 4),
        class_probabilities={c: round(p, 4) for c, p in zip(TUMOR_CLASSES, probs)},
        demo_mode=True, model_file=None,
    )


def predict(image_bytes: bytes) -> PredictionResult:
    _ensure_loaded()
    if _model is None:
        return _mock_prediction(image_bytes)
    import torch
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    with torch.no_grad():
        logits, u = _model(_preprocess(img))
    probs = torch.softmax(logits, dim=1).squeeze(0).tolist()
    u = u.squeeze().numpy()
    top = max(range(len(probs)), key=lambda i: probs[i])
    return PredictionResult(
        tumor_detected=TUMOR_CLASSES[top] != "no_tumor", tumor_type=TUMOR_CLASSES[top],
        confidence=round(probs[top], 4),
        class_probabilities={c: round(p, 4) for c, p in zip(TUMOR_CLASSES, probs)},
        demo_mode=False, model_file=MODEL_FILE.name,
        tumor_area_pct=round(float((u > 0.5).mean()) * 100, 2),
        heatmap=_heatmap_data_url(u, img.size),
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
