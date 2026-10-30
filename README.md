# NeuroCare — MRI Brain Tumor Detection (PINN + OpenAI)

A calm, bilingual (English / हिंदी) website that analyses a brain MRI with a trained
**PINN (Physics-Informed Neural Network)** model, shows a glowing **tumor heatmap**, and gives
gentle **AI guidance** (tumor information, nearby hospitals, specialists, emergency numbers).

- **Frontend:** plain HTML, CSS and JavaScript (`frontend/public/`)
- **Backend:** Python **Flask** (`backend/app.py`) that runs the PINN model and calls OpenAI
- **Database:** MongoDB (scans and Google sign-in accounts)

---

## 1. What you need on your computer

| Tool | Version | Download |
|---|---|---|
| Python | 3.10 – 3.12 | https://www.python.org/downloads/ |
| MongoDB Community Server | 6 or newer | https://www.mongodb.com/try/download/community |
| Git | any | https://git-scm.com/downloads |
| OpenAI API key | — | https://platform.openai.com/api-keys |

Make sure MongoDB is running (on Windows it usually starts as a service automatically;
on macOS with Homebrew: `brew services start mongodb-community`).

## 2. Get the code

```bash
git clone <your-repository-url> neurocare
cd neurocare/backend
```

## 3. Install the Python packages

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

The first install downloads PyTorch (CPU version, a few hundred MB), so it can take a few minutes.

## 4. Add your settings

Copy the example settings file and fill in your OpenAI key:

```bash
# Windows:      copy .env.example .env
# macOS/Linux:  cp .env.example .env
```

Open `backend/.env` and set:

```
MONGO_URL=mongodb://localhost:27017
DB_NAME=neurocare
OPENAI_API_KEY=sk-...your key...
OPENAI_MODEL=gpt-6.1-sol
PORT=5000
```

> Never share or commit your `.env` file — it contains your private OpenAI key.

## 5. Run it

```bash
python app.py
```

Open **http://localhost:5000** in Chrome or Edge. That's it — one command serves the
whole website and the API.

Sample MRI images to try are on the **Downloads** page (or in `backend/downloads/`).

---

## Project structure

```
backend/
  app.py                 Flask server: website + /api routes, sign-in, uploads
  ai_advice.py           OpenAI call (structured JSON, English or Hindi)
  models/
    pinn_model.pth       ← your trained PINN weights
    pinn_predictor.py    ← your exact ImprovedPINNCNN class + preprocessing + heatmap
  downloads/             files shown on the Downloads page
  uploads/               uploaded scans (created automatically)
  requirements.txt
  .env.example
  server.py              only used by the Emergent preview (not needed locally)
frontend/
  public/
    index.html           the whole website (single page, hash routes #/history, #/about, #/downloads)
    css/styles.css       design system
    js/app.js            language switch, sign-in, header, router
    js/scan.js           upload → prediction → heatmap → AI advice
    js/pages.js          My Scans, About, Downloads
    js/i18n.js           English + Hindi text
  package.json, src/     only used by the Emergent preview (not needed locally)
```

## Using your own / a new model

1. Put the weights in `backend/models/pinn_model.pth`.
2. If your architecture or training settings change, edit `ImprovedPINNCNN`,
   `IMG_SIZE`, `NORM_MEAN`, `NORM_STD` or `TUMOR_CLASSES` in `backend/models/pinn_predictor.py`.
3. Restart `python app.py`. The **About PINN** page shows whether the model loaded.

## API (all under `/api`)

| Method | Path | What it does |
|---|---|---|
| POST | `/api/predict` | multipart `mri` (image) + `location` → prediction, class probabilities, heatmap |
| POST | `/api/advice` | `{scan_id, language: "en" \| "hi"}` → AI guidance (cached per scan & language) |
| GET | `/api/model-status` | is the PINN model loaded |
| GET | `/api/my-scans` | signed-in user's saved scans |
| POST | `/api/auth/session` · GET `/api/auth/me` · POST `/api/auth/logout` | Google sign-in |
| GET | `/api/downloads` · `/api/downloads/<file>` | list / download sample files |

## Troubleshooting

- **"AI advice is not set up yet"** → add `OPENAI_API_KEY` to `backend/.env` and restart.
- **"Your OpenAI account has no credits left"** → add credits at platform.openai.com/settings/organization/billing.
- **"OpenAI rejected the API key"** → check `OPENAI_API_KEY` in `backend/.env`.
- **"OpenAI request failed … check OPENAI_MODEL"** → your account may not have that model;
  set `OPENAI_MODEL` to one you can use (for example `gpt-4o-mini`) and restart.
- **`ServerSelectionTimeoutError`** → MongoDB isn't running; start it and run `python app.py` again.
- **Google sign-in doesn't come back to the app** → sign-in uses Emergent's hosted Google login
  and needs internet; scanning, the heatmap and AI advice all work without signing in.

> NeuroCare is an educational project. It is not a medical device and does not give a diagnosis.
