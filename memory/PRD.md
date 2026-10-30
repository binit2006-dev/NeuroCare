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

## Implemented — Iteration 2 (Google Sign-in)
- Emergent-managed Google sign-in (optional; anonymous scanning still works)
- /api/auth/session, /api/auth/me, /api/auth/logout (cookie or Bearer), httpOnly 7-day session cookie
- Scans attached to user_id when signed in; /api/my-scans + /history "My Scans" page
- Ownership check on /api/scans/{id} and /api/advice for scans with a user_id
- CORS echoes origin with credentials

## Implemented — Iteration 3 (Real PINN model)
- User's checkpoint saved as backend/models/pinn_model.pth (state_dict); architecture rebuilt from tensor shapes in pinn_predictor.py (U-Net encoder/decoder + Fisher-KPP physics feats + classifier 259->128->4)
- Preprocess: RGB, 256x256, ImageNet normalisation; class order glioma, meningioma, no_tumor, pituitary (alphabetical ImageFolder assumption)
- Sanity check on 37 public Sartaj test MRIs: ~59% overall; pituitary/no_tumor/meningioma strong, glioma never predicted (mapped to meningioma) -> exact training preprocessing/physics features unconfirmed
- torch CPU added (requirements.txt has --extra-index-url for CPU wheels); 4 sample MRIs in downloads/

## Implemented — Iteration 4 (Exact model + Tumor Heatmap)
- pinn_predictor.py now uses user's exact ImprovedPINNCNN (notebook variant all_improvements: unet head; pool inside blocks; u_stats = mean/max/frac>0.5; 224px, ImageNet norm); strict state_dict load
- /api/predict returns heatmap (RGBA PNG data URL from 56x56 density map u, thresholded at 0.2, blurred coral glow) + tumor_area_pct (stored); heatmap not stored in Mongo
- HeatmapViewer on results: overlay on uploaded scan, pulsing glow, toggle + intensity slider
- Corrupt images -> 400; upload filenames sanitised
- Sample-set accuracy (public Sartaj test images): 20/37 — pituitary 7/7, no_tumor 9/10, meningioma 4/10, glioma 0/10 -> likely domain shift vs BrainTumor_RGB training data

## Implemented — Iteration 5 (Rewrite: plain HTML/CSS/JS + Flask, runnable locally)
- User request: frontend only HTML/CSS/JS, Flask backend running the PINN model, same features, clone-and-run for college demo. Choices: Flask, MongoDB, Emergent Google sign-in, user's own OpenAI key, replace React app.
- backend/app.py (Flask; serves frontend/public + /api), ai_advice.py (official openai SDK, Responses API json_schema strict, model gpt-6.1-sol via OPENAI_MODEL), server.py = a2wsgi adapter for Emergent preview only
- frontend/public: index.html (hash routes #/, #/history, #/about, #/downloads), css/styles.css, js/app.js, scan.js, pages.js, i18n.js (EN/HI); React src removed (src/index.js stub only)
- Security fixes: same-origin (no credentialed CORS), Lax cookie secure=request.is_secure, 10MB upload cap + PIL pixel cap, per-IP rate limits (remote_addr via ProxyFix), advice prompt built from stored scan, uploads no longer written to disk, torch weights_only, all UI text HTML-escaped
- README.md with local setup (python app.py -> http://localhost:5000), backend/.env.example
- Tests: 36 passed + 1 xfail (glioma accuracy); OPENAI account currently has NO CREDITS -> advice returns friendly 402 (EN/HI)

## Backlog
- **P1**: Google Places integration for real nearby hospitals (optional, requires API key)
- **P2**: PDF report export of results
- **P2**: Mobile camera capture for MRI
- **P2**: Multilingual support (Hindi, Spanish, etc.)

## Known Notes
- PINN model is REAL and matches notebook exactly. Low glioma recall on public Sartaj samples; verify on user's own BrainTumor_RGB Test set.
- GPT 6 Sol advice is REAL and uses `EMERGENT_LLM_KEY`.
