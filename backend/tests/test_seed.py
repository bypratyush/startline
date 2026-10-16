"""The seed catalogue is real research data: check it stays well formed."""

from datetime import date

from app.db import SessionLocal
from app.seed import load, read_data, validate


def test_seed_files_validate():
    data = read_data()
    assert validate(data) == []
    assert len(data["events"]) >= 200
    assert len(data["cities"]) == 36


def test_every_event_is_sourced_and_upcoming():
    for e in read_data()["events"]:
        assert e["sources"], e["slug"]
        assert date.fromisoformat(e["start_date"]) >= date(2026, 10, 15), e["slug"]
        assert e["date_status"] in ("confirmed", "expected")
        if e["date_status"] == "expected":
            assert e.get("last_edition_date") or e["sources"], e["slug"]


def test_no_em_dashes_in_text():
    for e in read_data()["events"]:
        for field in ("name", "summary", "venue"):
            assert "\u2014" not in (e.get(field) or ""), (e["slug"], field)


def test_seed_is_idempotent():
    with SessionLocal() as db:
        counts = load(db, read_data())
    assert counts["created_events"] == 0
