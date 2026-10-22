# 🧠 PINN Model Folder — Drop Your Trained Model Here

This folder is where you **add your trained PINN (Physics-Informed Neural Network) model** for brain tumor detection.

---

## 📂 Where to put your model

Drop one of the following files into this folder:

- `pinn_model.pth`  (PyTorch state dict — **recommended**)
- `pinn_model.pt`   (TorchScript / full PyTorch model)
- `pinn_model.h5`   (Keras / TensorFlow model)
- `pinn_model.onnx` (ONNX exported model)

The backend will automatically pick up the first file it finds in that priority order.

---

## 🔌 How it gets wired in

The file `pinn_predictor.py` (in this same folder) is the single integration point.
Open it and look for the function:

```python
def _load_model():
    ...
```

Replace the body with your own model-loading code. A commented reference
template for PyTorch is already there — just un-comment and adapt.

Then wire your inference inside:

```python
def predict(image_bytes: bytes) -> PredictionResult:
    ...
```

The rest of the application (API routes, frontend, OpenAI follow-up) will
work without any further changes.

---

## 🧪 Default behaviour (no model present)

If no model file is detected, the predictor runs in **DEMO MODE** and returns a
realistic mocked prediction so the full UX can be previewed end-to-end.
A banner is shown on the frontend when demo mode is active.

---

## 🏷️ Expected tumor classes

The default class order used across the app is:

1. `no_tumor`
2. `glioma`
3. `meningioma`
4. `pituitary`

If your model uses a different class order, update `TUMOR_CLASSES` in
`pinn_predictor.py`.
