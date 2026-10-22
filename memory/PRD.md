# NeuroCare — MRI Brain Tumor Detection

## Original Problem Statement
Web app for MRI Brain tumor detection. User's PINN model will be dropped into the backend. OpenAI (GPT 6 Sol) provides tumor info, nearby hospitals/doctors, emergency numbers, and medical advice. Educational, calming, mood-improving UX. Includes a downloads folder.

## Architecture
- **Backend**: FastAPI (`/app/backend/server.py`), MongoDB (motor), emergentintegrations (OpenAI GPT 6 Sol), Pillow.
- **PINN wrapper**: `/app/backend/models/pinn_predictor.py` — single integration point. User drops `pinn_model.pth/.pt/.h5/.onnx` into `/app/backend/models/`. Falls back to realistic mock (demo mode) until wired in.
- **Downloads**: `/app/backend/downloads/` folder is auto-served via `/api/downloads` + `/api/downloads/{file}`.
- **Frontend**: React + Tailwind + shadcn/ui + lucide + sonner. Pages: Home (hero → uploader → breathing loader → results), About (PINN explainer + model status), Downloads.
- **Design**: organic earthy palette (forest green #4A7c59, peach #E8B49B, sage), Outfit + DM Sans fonts, breathing animations, no clinical white or red.

## Core Requirements
- Patient uploads JPG/PNG MRI + enters city/pincode
- PINN model classifies into: no_tumor, glioma, meningioma, pituitary (+ confidence)
- GPT 6 Sol generates: tumor_info, next_steps, nearby_hospitals, recommended_specialists, emergency_contacts, mindset_tips (localised to patient location)
- No auth, no account

## Implemented (2026-02)
- Full E2E user flow (upload → scan → AI advice)
- `/api/predict` with multipart upload, 4-class probabilities, Mongo persistence
- `/api/advice` with GPT 6 Sol via Emergent Universal Key, strict JSON parsing
- `/api/model-status` for the About page
- `/api/downloads` list + file serving
- Calm UI with hero, breathing loader, bento results dashboard, emergency card, mindset card
- PINN integration folder with README + commented loader templates (PyTorch/TF/ONNX)

## Backlog
- **P1**: Save & resume past scans (local history list)
- **P1**: Google Places integration for real nearby hospitals (optional, requires API key)
- **P2**: PDF report export of results
- **P2**: Mobile camera capture for MRI
- **P2**: Multilingual support (Hindi, Spanish, etc.)

## Known Notes
- PINN model is MOCKED (demo_mode=true) until user drops their trained model into `/app/backend/models/`. Instructions are in `/app/backend/models/README.md` and in `pinn_predictor.py`.
- GPT 6 Sol advice is REAL and uses `EMERGENT_LLM_KEY`.
