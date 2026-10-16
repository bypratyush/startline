"""Tests run against a throwaway SQLite file seeded with the real catalogue.

DATABASE_URL and STARTLINE_TODAY have to be set before the app package is
imported, because the engine and settings are created at import time. "Today"
is pinned so that dates in the seed data give the same answers every run.
"""

import os
import tempfile

import pytest

_tmpdir = tempfile.mkdtemp(prefix="startline-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["STARTLINE_TODAY"] = "2026-10-15"
os.environ.setdefault("APP_ENV", "test")

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import load, read_data  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        load(db, read_data())
    yield


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


SWIMMER = {
    "name": "Test Swimmer",
    "email": "swimmer@example.com",
    "city": "bengaluru",
    "sports": [
        {"sport": "swimming", "answers": {"level": "beginner", "swim_nonstop": "400to1000", "swim_openwater": "some"}},
        {"sport": "triathlon", "answers": {"level": "beginner", "tri_experience": "none", "tri_weakest": "swim"}},
    ],
}

RUNNER = {
    "name": "Test Runner",
    "city": "mumbai",
    "sports": [
        {
            "sport": "running",
            "answers": {"level": "intermediate", "run_longest_recent": "11to21", "run_5k_band": "27to33"},
        }
    ],
}


@pytest.fixture()
def swimmer(client):
    resp = client.post("/api/athletes", json=SWIMMER)
    assert resp.status_code == 201, resp.text
    return resp.json()


@pytest.fixture()
def runner(client):
    resp = client.post("/api/athletes", json=RUNNER)
    assert resp.status_code == 201, resp.text
    return resp.json()


def registration_body(athlete_id, event, category_id, **extra):
    body = {
        "athlete_id": athlete_id,
        "event": event,
        "category_id": category_id,
        "full_name": "Test Athlete",
        "email": "athlete@example.com",
        "phone": "9876543210",
        "gender": "female",
        "date_of_birth": "1995-04-10",
        "tshirt_size": "M",
        "blood_group": "O+",
        "emergency_name": "Emergency Contact",
        "emergency_phone": "9123456780",
        "medical_declaration": True,
    }
    body.update(extra)
    return body
