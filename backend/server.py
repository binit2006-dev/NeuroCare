from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException, Request, Response
from fastapi.responses import FileResponse
from datetime import timedelta
import httpx
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import json
import re
import logging
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from emergentintegrations.llm.chat import LlmChat, UserMessage

from models import pinn_predictor

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")

DOWNLOADS_DIR = ROOT_DIR / "downloads"
UPLOADS_DIR = ROOT_DIR / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

app = FastAPI(title="NeuroCare - MRI Brain Tumor Detection API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None


class SessionRequest(BaseModel):
    session_id: str


class ScanRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    filename: str
    location: Optional[str] = None
    tumor_detected: bool
    tumor_type: str
    confidence: float
    class_probabilities: dict
    demo_mode: bool
    advice: Optional[dict] = None


class AdviceRequest(BaseModel):
    scan_id: str
    tumor_type: str
    confidence: float
    location: Optional[str] = ""
    tumor_detected: bool


# -----------------------------------------------------------------------------
# Auth (Emergent-managed Google sign-in)
# -----------------------------------------------------------------------------
EMERGENT_SESSION_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"
SESSION_DAYS = 7


def _get_token(request: Request) -> Optional[str]:
    token = request.cookies.get("session_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    return token


async def get_optional_user(request: Request) -> Optional[User]:
    token = _get_token(request)
    if not token:
        return None
    session = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not session:
        return None
    expires_at = session["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    user_doc = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0})
    return User(**user_doc) if user_doc else None


async def get_current_user(request: Request) -> User:
    user = await get_optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@api_router.post("/auth/session")
async def create_session(body: SessionRequest, response: Response):
    async with httpx.AsyncClient(timeout=15) as http:
        r = await http.get(EMERGENT_SESSION_URL, headers={"X-Session-ID": body.session_id})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session")
    data = r.json()

    existing = await db.users.find_one({"email": data["email"]}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": data["name"], "picture": data.get("picture")}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await db.users.insert_one({
            "user_id": user_id,
            "email": data["email"],
            "name": data["name"],
            "picture": data.get("picture"),
            "created_at": datetime.now(timezone.utc),
        })

    token = data["session_token"]
    await db.user_sessions.insert_one({
        "user_id": user_id,
        "session_token": token,
        "expires_at": datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS),
        "created_at": datetime.now(timezone.utc),
    })
    response.set_cookie(
        key="session_token", value=token, httponly=True, secure=True,
        samesite="none", path="/", max_age=SESSION_DAYS * 24 * 3600,
    )
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return User(**user_doc).model_dump()


@api_router.get("/auth/me")
async def auth_me(request: Request):
    user = await get_current_user(request)
    return user.model_dump()


@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    token = _get_token(request)
    if token:
        await db.user_sessions.delete_one({"session_token": token})
    response.delete_cookie("session_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@api_router.get("/my-scans")
async def my_scans(request: Request):
    user = await get_current_user(request)
    return await db.scans.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"status": "ok", "service": "NeuroCare MRI API"}


@api_router.get("/model-status")
async def model_status():
    return pinn_predictor.model_status()


@api_router.post("/predict")
async def predict(request: Request, mri: UploadFile = File(...), location: str = Form("")):
    user = await get_optional_user(request)
    if not mri.content_type or not mri.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload a valid MRI image (jpg/png).")

    image_bytes = await mri.read()
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    result = pinn_predictor.predict(image_bytes)

    scan_id = str(uuid.uuid4())
    saved_name = f"{scan_id}_{mri.filename}"
    (UPLOADS_DIR / saved_name).write_bytes(image_bytes)

    record = ScanRecord(
        id=scan_id,
        user_id=user.user_id if user else None,
        filename=mri.filename,
        location=location,
        tumor_detected=result.tumor_detected,
        tumor_type=result.tumor_type,
        confidence=result.confidence,
        class_probabilities=result.class_probabilities,
        demo_mode=result.demo_mode,
    )
    await db.scans.insert_one(record.model_dump())
    return record.model_dump()


def _build_prompt(req: AdviceRequest) -> str:
    confidence_pct = round(req.confidence * 100, 1)
    location_part = (
        f"The patient is located near: {req.location}."
        if req.location else "The patient's location is not provided."
    )

    if req.tumor_detected:
        header = (
            f"The MRI brain scan analysis suggests presence of a '{req.tumor_type}' type tumor "
            f"with {confidence_pct}% model confidence."
        )
    else:
        header = (
            f"The MRI brain scan analysis suggests NO tumor was detected "
            f"(model confidence {confidence_pct}%)."
        )

    return f"""{header}
{location_part}

Please respond ONLY with a valid JSON object (no markdown, no code fences) with the following keys:

{{
  "tumor_info": {{
    "name": "<common name of the tumor type, or 'Healthy Brain Scan' if no tumor>",
    "overview": "<2-3 compassionate, non-alarming sentences explaining what this is in plain language>",
    "common_symptoms": ["<symptom 1>", "<symptom 2>", "<symptom 3>", "<symptom 4>"],
    "severity_note": "<one calm sentence putting severity in context>"
  }},
  "next_steps": [
    "<clear next step 1 in plain language>",
    "<clear next step 2>",
    "<clear next step 3>",
    "<clear next step 4>"
  ],
  "nearby_hospitals": [
    {{"name": "<hospital name>", "specialty": "<specialty>", "city": "<city>", "notes": "<1-line note>"}},
    {{"name": "<hospital name>", "specialty": "<specialty>", "city": "<city>", "notes": "<1-line note>"}},
    {{"name": "<hospital name>", "specialty": "<specialty>", "city": "<city>", "notes": "<1-line note>"}},
    {{"name": "<hospital name>", "specialty": "<specialty>", "city": "<city>", "notes": "<1-line note>"}}
  ],
  "recommended_specialists": [
    {{"role": "<e.g. Neuro-oncologist>", "why": "<1-line reason>"}},
    {{"role": "<e.g. Neurosurgeon>", "why": "<1-line reason>"}},
    {{"role": "<e.g. Radiation Oncologist>", "why": "<1-line reason>"}}
  ],
  "emergency_contacts": [
    {{"label": "<e.g. National Emergency>", "number": "<phone>"}},
    {{"label": "<e.g. Ambulance>", "number": "<phone>"}},
    {{"label": "<e.g. Mental Health Helpline>", "number": "<phone>"}}
  ],
  "mindset_tips": [
    "<uplifting, evidence-based mental wellbeing tip 1>",
    "<tip 2>",
    "<tip 3>"
  ],
  "disclaimer": "This information is not a medical diagnosis. Please consult a qualified doctor."
}}

Use the patient's provided location to tailor hospital names and emergency numbers to the correct country. If location is unknown, give widely-known international options and clearly say so in notes. Keep tone warm, hopeful, and empowering."""


async def _get_owned_scan(scan_id: str, request: Request) -> dict:
    doc = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if doc.get("user_id"):
        user = await get_optional_user(request)
        if not user or user.user_id != doc["user_id"]:
            raise HTTPException(status_code=404, detail="Scan not found.")
    return doc


@api_router.post("/advice")
async def advice(req: AdviceRequest, request: Request):
    await _get_owned_scan(req.scan_id, request)
    if not EMERGENT_LLM_KEY:
        raise HTTPException(status_code=500, detail="LLM key not configured.")

    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=f"advice-{req.scan_id}",
        system_message=(
            "You are a compassionate medical information assistant. You never give a diagnosis; "
            "you provide clear, calm, hopeful educational information and point patients to the "
            "right professionals. Always respond with pure JSON when asked."
        ),
    ).with_model("openai", "gpt-6-sol")

    try:
        response = await chat.send_message(UserMessage(text=_build_prompt(req)))
    except Exception as exc:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    text = response if isinstance(response, str) else str(response)
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise HTTPException(status_code=502, detail="LLM response was not valid JSON.")
        parsed = json.loads(match.group(0))

    await db.scans.update_one({"id": req.scan_id}, {"$set": {"advice": parsed}})
    return parsed


@api_router.get("/scans/{scan_id}")
async def get_scan(scan_id: str, request: Request):
    return await _get_owned_scan(scan_id, request)


# -----------------------------------------------------------------------------
# Downloads
# -----------------------------------------------------------------------------
@api_router.get("/downloads")
async def list_downloads():
    files = []
    for p in sorted(DOWNLOADS_DIR.iterdir()):
        if p.is_file() and not p.name.startswith("."):
            files.append({
                "name": p.name,
                "size_bytes": p.stat().st_size,
                "ext": p.suffix.lstrip("."),
            })
    return files


@api_router.get("/downloads/{filename}")
async def download_file(filename: str):
    safe = Path(filename).name
    target = DOWNLOADS_DIR / safe
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path=target, filename=safe)


app.include_router(api_router)

_cors = os.environ.get("CORS_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[] if _cors == "*" else _cors.split(","),
    allow_origin_regex=".*" if _cors == "*" else None,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
