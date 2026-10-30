"""NeuroCare — Flask backend (serves the website, the PINN model API and AI advice)."""
import logging
import os
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, UnidentifiedImageError
from pymongo import MongoClient
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.middleware.proxy_fix import ProxyFix

from models import pinn_predictor

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL") or "gpt-6.1-sol"

WEBSITE_DIR = (ROOT_DIR.parent / "frontend" / "public").resolve()
DOWNLOADS_DIR = ROOT_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_MB = 10
Image.MAX_IMAGE_PIXELS = 40_000_000
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
SESSION_DAYS = 7

mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("neurocare")


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
def error(message, status):
    return jsonify({"detail": message}), status


def now():
    return datetime.now(timezone.utc)


_hits = defaultdict(deque)
_hits_lock = threading.Lock()


def rate_limited(bucket, limit, window_s=600):
    ip = request.remote_addr or "?"  # ProxyFix already resolved the trusted proxy hop
    key, t = (bucket, ip), time.time()
    with _hits_lock:
        q = _hits[key]
        while q and q[0] < t - window_s:
            q.popleft()
        if len(q) >= limit:
            return True
        q.append(t)
    return False


def get_token():
    token = request.cookies.get("session_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    return token


def current_user():
    token = get_token()
    if not token:
        return None
    session = db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        return None
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < now():
        return None
    return db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "created_at": 0})


def owned_scan(scan_id):
    doc = db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not doc:
        return None
    if doc.get("user_id"):
        user = current_user()
        if not user or user["user_id"] != doc["user_id"]:
            return None
    return doc


@app.errorhandler(RequestEntityTooLarge)
def too_large(_):
    return error(f"File is too large. Maximum size is {MAX_UPLOAD_MB} MB.", 413)


# ----------------------------------------------------------------------------
# Website (static HTML/CSS/JS)
# ----------------------------------------------------------------------------
@app.get("/")
def index():
    return send_from_directory(WEBSITE_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        return error("Not found", 404)
    return send_from_directory(WEBSITE_DIR, path)


# ----------------------------------------------------------------------------
# Auth (Emergent-managed Google sign-in)
# ----------------------------------------------------------------------------
@app.post("/api/auth/session")
def create_session():
    session_id = (request.get_json(silent=True) or {}).get("session_id")
    if not session_id:
        return error("session_id is required", 400)
    try:
        r = requests.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": session_id}, timeout=15)
    except requests.RequestException:
        return error("Sign-in service is unreachable. Check your internet connection.", 503)
    if r.status_code != 200:
        return error("Invalid session", 401)
    try:
        data = r.json()
        email, name, token = data["email"], data["name"], data["session_token"]
    except (ValueError, KeyError, TypeError):
        return error("Invalid session", 401)

    existing = db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        db.users.update_one({"user_id": user_id}, {"$set": {"name": name, "picture": data.get("picture")}})
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        db.users.insert_one({
            "user_id": user_id, "email": email, "name": name,
            "picture": data.get("picture"), "created_at": now(),
        })

    db.user_sessions.insert_one({
        "user_id": user_id, "session_token": token,
        "expires_at": now() + timedelta(days=SESSION_DAYS), "created_at": now(),
    })
    user = db.users.find_one({"user_id": user_id}, {"_id": 0, "created_at": 0})
    resp = jsonify(user)
    # Website and API share one origin, so a Lax cookie works on localhost (http) and https.
    resp.set_cookie("session_token", token, httponly=True, secure=request.is_secure,
                    samesite="Lax", path="/", max_age=SESSION_DAYS * 24 * 3600)
    return resp


@app.get("/api/auth/me")
def auth_me():
    user = current_user()
    return jsonify(user) if user else error("Not authenticated", 401)


@app.post("/api/auth/logout")
def logout():
    token = get_token()
    if token:
        db.user_sessions.delete_one({"session_token": token})
    resp = jsonify({"ok": True})
    resp.delete_cookie("session_token", path="/", secure=request.is_secure, samesite="Lax")
    return resp


# ----------------------------------------------------------------------------
# PINN prediction
# ----------------------------------------------------------------------------
@app.get("/api/")
def root():
    return jsonify({"status": "ok", "service": "NeuroCare MRI API (Flask)"})


@app.get("/api/model-status")
def model_status():
    return jsonify(pinn_predictor.model_status())


@app.post("/api/predict")
def predict():
    if rate_limited("predict", 30):
        return error("Too many scans from this device. Please wait a few minutes.", 429)
    mri = request.files.get("mri")
    if not mri or not (mri.mimetype or "").startswith("image/"):
        return error("Please upload a valid MRI image (jpg/png).", 400)
    image_bytes = mri.read()
    if not image_bytes:
        return error("Empty file.", 400)
    try:
        result = pinn_predictor.predict(image_bytes)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return error("Please upload a valid MRI image (jpg/png).", 400)

    user = current_user()
    scan_id = str(uuid.uuid4())
    record = {
        "id": scan_id,
        "user_id": user["user_id"] if user else None,
        "created_at": now().isoformat(),
        "filename": Path(mri.filename or "scan").name[:120],
        "location": (request.form.get("location") or "")[:120],
        "tumor_detected": result.tumor_detected,
        "tumor_type": result.tumor_type,
        "confidence": result.confidence,
        "class_probabilities": result.class_probabilities,
        "demo_mode": result.demo_mode,
        "tumor_area_pct": result.tumor_area_pct,
    }
    db.scans.insert_one(dict(record))
    return jsonify({**record, "heatmap": result.heatmap})


@app.get("/api/scans/<scan_id>")
def get_scan(scan_id):
    doc = owned_scan(scan_id)
    return jsonify(doc) if doc else error("Scan not found.", 404)


@app.get("/api/my-scans")
def my_scans():
    user = current_user()
    if not user:
        return error("Not authenticated", 401)
    docs = list(db.scans.find({"user_id": user["user_id"]}, {"_id": 0}).sort("created_at", -1).limit(100))
    return jsonify(docs)


# ----------------------------------------------------------------------------
# AI advice (OpenAI, user's own key)
# ----------------------------------------------------------------------------
ADVICE_FIELD = {"en": "advice", "hi": "advice_hi"}
_advice_locks = {}
_locks_guard = threading.Lock()


def _with_advice_lock(key, fn):
    with _locks_guard:
        entry = _advice_locks.setdefault(key, [threading.Lock(), 0])
        entry[1] += 1
    try:
        with entry[0]:
            return fn()
    finally:
        with _locks_guard:
            entry[1] -= 1
            if entry[1] == 0:
                _advice_locks.pop(key, None)


@app.post("/api/advice")
def advice():
    body = request.get_json(silent=True) or {}
    language = body.get("language", "en")
    if language not in ADVICE_FIELD:
        return error("language must be 'en' or 'hi'", 422)
    scan = owned_scan(str(body.get("scan_id", "")))
    if not scan:
        return error("Scan not found.", 404)

    field = ADVICE_FIELD[language]

    def produce():
        cached = db.scans.find_one({"id": scan["id"]}, {"_id": 0, field: 1}).get(field)
        if cached:
            return jsonify(cached)
        if not OPENAI_API_KEY:
            return error("AI advice is not set up yet. Add OPENAI_API_KEY to backend/.env and restart.", 503)
        if rate_limited("advice", 40):
            return error("Too many advice requests. Please wait a few minutes.", 429)
        from ai_advice import AdviceError, generate_advice
        try:
            parsed = generate_advice(scan, language, OPENAI_API_KEY, OPENAI_MODEL)
        except AdviceError as exc:
            return error(str(exc), exc.status)
        db.scans.update_one({"id": scan["id"]}, {"$set": {field: parsed}})
        return jsonify(parsed)

    return _with_advice_lock((scan["id"], language), produce)


# ----------------------------------------------------------------------------
# Downloads
# ----------------------------------------------------------------------------
@app.get("/api/downloads")
def list_downloads():
    files = [
        {"name": p.name, "size_bytes": p.stat().st_size, "ext": p.suffix.lstrip(".")}
        for p in sorted(DOWNLOADS_DIR.iterdir())
        if p.is_file() and not p.name.startswith(".")
    ]
    return jsonify(files)


@app.get("/api/downloads/<path:filename>")
def download_file(filename):
    safe = Path(filename).name
    if not (DOWNLOADS_DIR / safe).is_file():
        return error("File not found.", 404)
    return send_from_directory(DOWNLOADS_DIR, safe, as_attachment=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"\n  NeuroCare is running ->  http://localhost:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
