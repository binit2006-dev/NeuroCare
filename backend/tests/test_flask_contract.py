# Flask rewrite contract tests: root, advice (scan_id+language, 402 no-credits path), ownership, security (413/400/traversal/CORS)
import io
import os
import subprocess
import time

import pytest
import requests
from PIL import Image

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    for line in open("/app/frontend/.env"):
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")
SAMPLES = "/app/scripts/mri_samples"


def _mk_session(tag):
    t = f"{int(time.time()*1000)}_{tag}"
    uid, tok = f"test-user-{t}", f"test_session_{t}"
    js = (f"use('test_database');"
          f"db.users.insertOne({{user_id:'{uid}',email:'test.user.{t}@example.com',name:'Test {tag}',picture:null,created_at:new Date()}});"
          f"db.user_sessions.insertOne({{user_id:'{uid}',session_token:'{tok}',expires_at:new Date(Date.now()+7*864e5),created_at:new Date()}});")
    subprocess.run(["mongosh", "--quiet", "--eval", js], check=True, capture_output=True)
    return uid, tok


def _predict(name="pituitary_tumor_5.jpg", headers=None, location="Mumbai"):
    with open(f"{SAMPLES}/{name}", "rb") as f:
        return requests.post(f"{BASE_URL}/api/predict", headers=headers or {},
                             files={"mri": (f"TEST_{name}", f, "image/jpeg")},
                             data={"location": location}, timeout=120)


@pytest.fixture(scope="module")
def user():
    return _mk_session("FC")


@pytest.fixture(scope="module")
def anon_scan():
    r = _predict("no_tumor_1.jpg")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="module")
def owned_scan(user):
    r = _predict("pituitary_tumor_5.jpg", headers={"Authorization": f"Bearer {user[1]}"})
    assert r.status_code == 200, r.text
    return r.json()


# --- basics
def test_root():
    r = requests.get(f"{BASE_URL}/api/")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_predict_shape(anon_scan):
    d = anon_scan
    for k in ["id", "tumor_type", "confidence", "class_probabilities", "demo_mode", "tumor_area_pct", "heatmap", "location"]:
        assert k in d
    assert d["demo_mode"] is False and d["heatmap"].startswith("data:image/png;base64,")
    assert d["tumor_type"] == "no_tumor" and d["location"] == "Mumbai"


# --- scan ownership
def test_owned_scan_hidden_from_anon_and_others(user, owned_scan):
    sid = owned_scan["id"]
    assert requests.get(f"{BASE_URL}/api/scans/{sid}").status_code == 404
    _, other = _mk_session("FC2")
    assert requests.get(f"{BASE_URL}/api/scans/{sid}", headers={"Authorization": f"Bearer {other}"}).status_code == 404
    r = requests.get(f"{BASE_URL}/api/scans/{sid}", headers={"Authorization": f"Bearer {user[1]}"})
    assert r.status_code == 200 and r.json()["user_id"] == user[0] and "heatmap" not in r.json()


def test_my_scans_contains_owned(user, owned_scan):
    r = requests.get(f"{BASE_URL}/api/my-scans", headers={"Authorization": f"Bearer {user[1]}"})
    assert r.status_code == 200 and r.json()[0]["id"] == owned_scan["id"]


# --- advice (new contract: only scan_id + language)
def test_advice_invalid_language_422(anon_scan):
    r = requests.post(f"{BASE_URL}/api/advice", json={"scan_id": anon_scan["id"], "language": "fr"})
    assert r.status_code == 422


def test_advice_unknown_scan_404():
    r = requests.post(f"{BASE_URL}/api/advice", json={"scan_id": "does-not-exist", "language": "en"})
    assert r.status_code == 404


def test_advice_other_users_scan_404(owned_scan):
    r = requests.post(f"{BASE_URL}/api/advice", json={"scan_id": owned_scan["id"], "language": "en"})
    assert r.status_code == 404


def test_advice_no_credits_402(anon_scan):
    r = requests.post(f"{BASE_URL}/api/advice", json={"scan_id": anon_scan["id"], "language": "en"}, timeout=120)
    assert r.status_code == 402, r.text
    assert "no credits" in r.json()["detail"]


def test_advice_owner_hi_402(user, owned_scan):
    r = requests.post(f"{BASE_URL}/api/advice", json={"scan_id": owned_scan["id"], "language": "hi"},
                      headers={"Authorization": f"Bearer {user[1]}"}, timeout=120)
    assert r.status_code == 402, r.text


# --- security
def test_upload_too_large_413():
    big = b"\xff\xd8" + os.urandom(11 * 1024 * 1024)
    r = requests.post(f"{BASE_URL}/api/predict", files={"mri": ("TEST_big.jpg", big, "image/jpeg")}, timeout=120)
    assert r.status_code == 413, r.status_code
    assert "too large" in r.json()["detail"].lower()


def test_corrupt_image_400():
    r = requests.post(f"{BASE_URL}/api/predict", files={"mri": ("TEST_bad.jpg", b"garbage", "image/jpeg")})
    assert r.status_code == 400


def test_missing_file_400():
    r = requests.post(f"{BASE_URL}/api/predict", data={"location": "x"})
    assert r.status_code == 400


@pytest.mark.parametrize("path", ["/api/downloads/..%2F.env", "/api/downloads/..%2Fapp.py",
                                  "/api/downloads/%2E%2E%2F%2E%2E%2Fbackend%2F.env"])
def test_download_traversal_404(path):
    r = requests.get(f"{BASE_URL}{path}")
    assert r.status_code == 404
    assert "MONGO_URL" not in r.text and "OPENAI" not in r.text


def test_download_file_ok():
    r = requests.get(f"{BASE_URL}/api/downloads/sample_glioma.jpg")
    assert r.status_code == 200 and r.content[:2] == b"\xff\xd8"
    assert "attachment" in r.headers.get("content-disposition", "")


def test_download_missing_404():
    assert requests.get(f"{BASE_URL}/api/downloads/nope.jpg").status_code == 404


def test_no_allow_credentials_header():
    r = requests.get(f"{BASE_URL}/api/", headers={"Origin": "https://evil.test"})
    assert r.headers.get("access-control-allow-credentials") != "true"
    assert r.headers.get("access-control-allow-origin") in (None, "*")
