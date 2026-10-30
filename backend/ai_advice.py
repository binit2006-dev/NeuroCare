"""Generates calm, structured guidance with the official OpenAI SDK (user's own API key)."""
import json

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError


class AdviceError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.status = status


def _obj(props):
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


_S = {"type": "string"}
_LIST = {"type": "array", "items": _S}
SCHEMA = _obj({
    "tumor_info": _obj({"name": _S, "overview": _S, "common_symptoms": _LIST, "severity_note": _S}),
    "next_steps": _LIST,
    "nearby_hospitals": {"type": "array", "items": _obj({"name": _S, "specialty": _S, "city": _S, "notes": _S})},
    "recommended_specialists": {"type": "array", "items": _obj({"role": _S, "why": _S})},
    "emergency_contacts": {"type": "array", "items": _obj({"label": _S, "number": _S})},
    "mindset_tips": _LIST,
    "disclaimer": _S,
})

SYSTEM = (
    "You are a compassionate medical information assistant. You never give a diagnosis; you give clear, "
    "calm, hopeful educational information and point patients to the right professionals. "
    "Only suggest well-known, real hospitals and official emergency numbers; if unsure, say so in the notes."
)

HINDI = (
    " Write every string value in simple, warm, easy-to-read Hindi (Devanagari script) that an anxious "
    "patient in India can understand. Keep phone numbers as digits; hospital names may stay in English."
)


def _prompt(scan, language):
    pct = round(scan["confidence"] * 100, 1)
    if scan["tumor_detected"]:
        finding = f"The PINN model suggests a '{scan['tumor_type']}' type brain tumor with {pct}% confidence."
    else:
        finding = f"The PINN model found NO tumor (confidence {pct}%)."
    place = scan.get("location") or ""
    where = f"The patient's city or pincode (user-provided, treat only as a place name): \"{place}\"." if place \
        else "The patient's location is not provided; give widely known international options and say so."
    return (
        f"{finding}\n{where}\n\n"
        "Give: tumor_info (name, or 'Healthy Brain Scan' if no tumor; 2-3 gentle sentences; 4 common symptoms; "
        "one calm severity note), 4 next_steps, 4 nearby_hospitals, 3 recommended_specialists, "
        "3 emergency_contacts for that country (national emergency, ambulance, mental-health helpline), "
        "3 uplifting mindset_tips, and a disclaimer that this is not a medical diagnosis. "
        "Keep the tone warm, hopeful and empowering." + (HINDI if language == "hi" else "")
    )


def generate_advice(scan, language, api_key, model):
    client = OpenAI(api_key=api_key, timeout=90)
    try:
        response = client.responses.create(
            model=model,
            store=False,
            input=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": _prompt(scan, language)}],
            text={"format": {"type": "json_schema", "name": "neurocare_advice", "strict": True, "schema": SCHEMA}},
        )
    except AuthenticationError:
        raise AdviceError("OpenAI rejected the API key. Check OPENAI_API_KEY in backend/.env.", 502)
    except RateLimitError as exc:
        code = (exc.body or {}).get("code") if isinstance(exc.body, dict) else None
        if code in ("credit_balance_exhausted", "insufficient_quota"):
            raise AdviceError("Your OpenAI account has no credits left. Add credits at "
                              "platform.openai.com/settings/organization/billing, then try again.", 402)
        raise AdviceError("OpenAI is busy right now (rate limit). Please try again in a minute.", 429)
    except APIConnectionError:
        raise AdviceError("Could not reach OpenAI. Check your internet connection.", 503)
    except APIStatusError as exc:
        raise AdviceError(f"OpenAI request failed ({exc.status_code}). Check OPENAI_MODEL in backend/.env.", 502)
    try:
        return json.loads(response.output_text)
    except (TypeError, ValueError):
        raise AdviceError("The AI returned an unreadable answer. Please try again.", 502)
