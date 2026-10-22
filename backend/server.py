from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
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
class ScanRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
# Routes
# -----------------------------------------------------------------------------
@api_router.get("/")
async def root():
    return {"status": "ok", "service": "NeuroCare MRI API"}


@api_router.get("/model-status")
async def model_status():
    return pinn_predictor.model_status()


@api_router.post("/predict")
async def predict(mri: UploadFile = File(...), location: str = Form("")):
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


@api_router.post("/advice")
async def advice(req: AdviceRequest):
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
async def get_scan(scan_id: str):
    doc = await db.scans.find_one({"id": scan_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return doc


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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
