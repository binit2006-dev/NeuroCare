# Auth (Emergent Google) + my-scans + predict user attach tests
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


def _mk_session(tag):
    t = f"{int(time.time()*1000)}_{tag}"
    uid, tok = f"test-user-{t}", f"test_session_{t}"
    js = (f"use('test_database');"
          f"db.users.insertOne({{user_id:'{uid}',email:'test.user.{t}@example.com',name:'Test {tag}',picture:null,created_at:new Date()}});"
          f"db.user_sessions.insertOne({{user_id:'{uid}',session_token:'{tok}',expires_at:new Date(Date.now()+7*864e5),created_at:new Date()}});")
    subprocess.run(["mongosh", "--quiet", "--eval", js], check=True, capture_output=True)
    return uid, tok


def _jpg():
    b = io.BytesIO()
    Image.new("RGB", (64, 64), (120, 120, 120)).save(b, "JPEG")
    return b.getvalue()


@pytest.fixture(scope="module")
def user_a():
    return _mk_session("A")


@pytest.fixture(scope="module")
def user_b():
    return _mk_session("B")


# --- /auth/me
def test_me_unauth():
    assert requests.get(f"{BASE_URL}/api/auth/me").status_code == 401


def test_me_bearer(user_a):
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {user_a[1]}"})
    assert r.status_code == 200
    d = r.json()
    assert d["user_id"] == user_a[0] and "_id" not in d
    assert set(["user_id", "email", "name", "picture"]).issubset(d)


def test_me_cookie(user_a):
    r = requests.get(f"{BASE_URL}/api/auth/me", cookies={"session_token": user_a[1]})
    assert r.status_code == 200 and r.json()["user_id"] == user_a[0]


def test_me_bad_token():
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": "Bearer nope"})
    assert r.status_code == 401


# --- /my-scans + /predict
def test_my_scans_unauth():
    assert requests.get(f"{BASE_URL}/api/my-scans").status_code == 401


def test_predict_auth_and_my_scans_isolation(user_a, user_b):
    h = {"Authorization": f"Bearer {user_a[1]}"}
    ids = []
    for i in range(2):
        r = requests.post(f"{BASE_URL}/api/predict", headers=h,
                          files={"mri": (f"TEST_{i}.jpg", _jpg(), "image/jpeg")}, data={"location": "Mumbai"})
        assert r.status_code == 200
        assert r.json()["user_id"] == user_a[0]
        ids.append(r.json()["id"])
        time.sleep(0.05)
    r = requests.get(f"{BASE_URL}/api/my-scans", headers=h)
    assert r.status_code == 200
    scans = r.json()
    assert [s["id"] for s in scans[:2]] == [ids[1], ids[0]]  # newest first
    assert all(s["user_id"] == user_a[0] for s in scans)
    assert all("_id" not in s for s in scans)
    rb = requests.get(f"{BASE_URL}/api/my-scans", headers={"Authorization": f"Bearer {user_b[1]}"})
    assert rb.status_code == 200 and rb.json() == []


def test_predict_anonymous():
    r = requests.post(f"{BASE_URL}/api/predict",
                      files={"mri": ("TEST_anon.jpg", _jpg(), "image/jpeg")}, data={"location": "Delhi"})
    assert r.status_code == 200
    d = r.json()
    assert d["user_id"] is None and "tumor_type" in d


# --- /auth/session
def test_session_invalid():
    r = requests.post(f"{BASE_URL}/api/auth/session", json={"session_id": "bogus"})
    assert r.status_code == 401


# --- /auth/logout
def test_logout_cookie():
    _, tok = _mk_session("L1")
    r = requests.post(f"{BASE_URL}/api/auth/logout", cookies={"session_token": tok})
    assert r.status_code == 200 and r.json() == {"ok": True}
    sc = r.headers.get("set-cookie", "")
    assert "session_token=" in sc
    assert requests.get(f"{BASE_URL}/api/auth/me", cookies={"session_token": tok}).status_code == 401


def test_logout_bearer():
    _, tok = _mk_session("L2")
    h = {"Authorization": f"Bearer {tok}"}
    requests.post(f"{BASE_URL}/api/auth/logout", headers=h)
    assert requests.get(f"{BASE_URL}/api/auth/me", headers=h).status_code == 401, \
        "logout ignores Bearer token; session not deleted"


# --- CORS (new contract: app must NOT send Allow-Credentials; gateway may add plain '*')
def test_cors_no_credentials():
    origin = "https://example-origin.test"
    r = requests.get(f"{BASE_URL}/api/auth/me", headers={"Origin": origin})
    assert r.headers.get("access-control-allow-credentials") != "true"
    assert r.headers.get("access-control-allow-origin") in (None, "*")
