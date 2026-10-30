# Hindi mode: /api/advice language=hi|en caching, Devanagari output, 422 on invalid language
import os
import re
import time
import subprocess
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

SAMPLE = "/app/scripts/mri_samples/pituitary_tumor_5.jpg"
DEV = re.compile(r"[\u0900-\u097F]")
KEYS = {"tumor_info", "next_steps", "nearby_hospitals", "recommended_specialists",
        "emergency_contacts", "mindset_tips", "disclaimer"}


def _mk_session():
    t = f"{int(time.time()*1000)}_hi"
    uid, tok = f"test-user-{t}", f"test_session_{t}"
    js = (f"use('test_database');"
          f"db.users.insertOne({{user_id:'{uid}',email:'test.user.{t}@example.com',name:'Hindi Tester',picture:null,created_at:new Date()}});"
          f"db.user_sessions.insertOne({{user_id:'{uid}',session_token:'{tok}',expires_at:new Date(Date.now()+7*864e5),created_at:new Date()}});")
    subprocess.run(["mongosh", "--quiet", "--eval", js], check=True, capture_output=True)
    return uid, tok


@pytest.fixture(scope="module")
def session():
    return _mk_session()


@pytest.fixture(scope="module")
def scan(session):
    with open(SAMPLE, "rb") as f:
        r = requests.post(f"{BASE_URL}/api/predict",
                          headers={"Authorization": f"Bearer {session[1]}"},
                          files={"mri": ("pituitary_tumor_5.jpg", f, "image/jpeg")},
                          data={"location": "Mumbai"}, timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


def _body(scan, lang):
    return {"scan_id": scan["id"], "tumor_type": scan["tumor_type"], "confidence": scan["confidence"],
            "location": scan["location"], "tumor_detected": scan["tumor_detected"], "language": lang}


def _post(scan, session, lang):
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/advice", json=_body(scan, lang),
                      headers={"Authorization": f"Bearer {session[1]}"}, timeout=150)
    return r, time.time() - t0


def _mongo_scan(sid):
    out = subprocess.run(["mongosh", "--quiet", "--eval",
                          f"use('test_database'); const d=db.scans.findOne({{id:'{sid}'}}); "
                          f"print(JSON.stringify({{en: !!d.advice, hi: !!d.advice_hi}}))"],
                         capture_output=True, text=True, check=True)
    import json
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_predict_pituitary(scan):
    assert scan["tumor_type"] == "pituitary"


def test_invalid_language_422(scan, session):
    r, _ = _post(scan, session, "fr")
    assert r.status_code == 422


def test_hindi_advice_devanagari(scan, session):
    r, dt = _post(scan, session, "hi")
    assert r.status_code == 200, r.text
    d = r.json()
    print(f"hi uncached: {dt:.1f}s")
    assert KEYS.issubset(d.keys())
    assert DEV.search(d["tumor_info"]["overview"])
    assert DEV.search(d["disclaimer"])
    assert all(DEV.search(s) for s in d["next_steps"])
    assert all(DEV.search(s) for s in d["mindset_tips"])
    st = _mongo_scan(scan["id"])
    assert st["hi"] is True and st["en"] is False


def test_hindi_cached_fast(scan, session):
    r, dt = _post(scan, session, "hi")
    print(f"hi cached: {dt:.2f}s")
    assert r.status_code == 200 and dt < 3
    assert DEV.search(r.json()["tumor_info"]["overview"])


def test_english_advice_separate(scan, session):
    r, dt = _post(scan, session, "en")
    assert r.status_code == 200, r.text
    d = r.json()
    print(f"en uncached: {dt:.1f}s")
    assert KEYS.issubset(d.keys())
    assert not DEV.search(d["tumor_info"]["overview"])
    st = _mongo_scan(scan["id"])
    assert st["hi"] is True and st["en"] is True
    r2, dt2 = _post(scan, session, "en")
    assert dt2 < 3 and r2.json() == d


def test_default_language_en(scan, session):
    b = _body(scan, "en"); b.pop("language")
    r = requests.post(f"{BASE_URL}/api/advice", json=b, headers={"Authorization": f"Bearer {session[1]}"}, timeout=30)
    assert r.status_code == 200 and not DEV.search(r.json()["tumor_info"]["overview"])


def test_my_scans_has_advice_hi(scan, session):
    r = requests.get(f"{BASE_URL}/api/my-scans", headers={"Authorization": f"Bearer {session[1]}"})
    s = next(x for x in r.json() if x["id"] == scan["id"])
    assert "_id" not in s and s.get("advice_hi") and s.get("advice")


def test_other_user_cannot_get_advice(scan):
    r = requests.post(f"{BASE_URL}/api/advice", json=_body(scan, "hi"), timeout=30)
    assert r.status_code == 404
