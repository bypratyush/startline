"""Load the reference catalogue (cities, sports, events) from JSON into the database.

    python -m app.seed            # upsert everything, safe to run repeatedly
    python -m app.seed --check    # validate the JSON files only

The JSON lives in app/seed/data. Events were researched from organiser websites
and registration platforms; every event keeps its source URLs.

Upserts are keyed on slugs (and category names within an event), so
re-running the seed after editing a file updates rows in place and never
touches athlete data such as registrations.
"""

import json
import logging
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..db import SessionLocal, engine
from ..models import City, Event, EventCategory, Registration, Sport

DATA = Path(__file__).parent / "data"
SEED_LOCK_ID = 2026_1016
log = logging.getLogger("startline.seed")

EVENT_FIELDS = (
    "name",
    "edition",
    "discipline",
    "venue",
    "organiser",
    "official_url",
    "registration_status",
    "registration_url",
    "registration_notes",
    "summary",
    "course",
    "format",
    "highlights",
    "tips",
    "amenities",
    "beginner_friendly",
    "tags",
    "sources",
)
CATEGORY_FIELDS = (
    "distance_km",
    "swim_km",
    "bike_km",
    "run_km",
    "fee_inr",
    "start_time",
    "cutoff_minutes",
    "min_age",
    "level",
    "eligibility",
    "notes",
)
SPORT_FIELDS = (
    "name",
    "family",
    "color",
    "sort_order",
    "tagline",
    "description",
    "disciplines",
    "questions",
    "level_definitions",
    "recommendation_rules",
    "guide",
    "sources",
)
CITY_FIELDS = ("name", "state", "tier", "lat", "lon", "elevation_m", "climate", "air_quality_note", "sports_note")


def _d(value):
    return date.fromisoformat(value) if value else None


def read_data(data_dir: Path = DATA) -> dict:
    cities = json.loads((data_dir / "cities.json").read_text())["cities"]
    sports = json.loads((data_dir / "sports.json").read_text())["sports"]
    events = []
    for f in sorted((data_dir / "events").glob("*.json")):
        events.extend(json.loads(f.read_text())["events"])
    return {"cities": cities, "sports": sports, "events": events}


def validate(data: dict) -> list[str]:
    problems = []
    city_slugs = {c["slug"] for c in data["cities"]}
    sport_slugs = {s["slug"] for s in data["sports"]}
    seen = set()
    for s in data["sports"]:
        if not 2 <= len(s["questions"]) <= 3:
            problems.append(f"sport {s['slug']}: needs 2-3 profile questions, has {len(s['questions'])}")
    for e in data["events"]:
        tag = e.get("slug", e.get("name"))
        if e["slug"] in seen:
            problems.append(f"duplicate event slug {e['slug']}")
        seen.add(e["slug"])
        if e["sport"] not in sport_slugs:
            problems.append(f"{tag}: unknown sport {e['sport']}")
        if e["city"] not in city_slugs:
            problems.append(f"{tag}: unknown city {e['city']}")
        if not e.get("categories"):
            problems.append(f"{tag}: no categories")
        names = [c["name"] for c in e.get("categories", [])]
        if len(names) != len(set(names)):
            problems.append(f"{tag}: duplicate category names")
        if _d(e["end_date"]) < _d(e["start_date"]):
            problems.append(f"{tag}: ends before it starts")
    return problems


def _upsert(db: Session, model, key: str, value, fields, row: dict):
    obj = db.scalar(select(model).where(getattr(model, key) == value))
    created = obj is None
    if created:
        obj = model(**{key: value})
        db.add(obj)
    for f in fields:
        if f in row:
            setattr(obj, f, row[f])
    return obj, created


def load(db: Session, data: dict) -> dict:
    counts = {"cities": 0, "sports": 0, "events": 0, "categories": 0, "created_events": 0}
    cities = {}
    for row in data["cities"]:
        obj, _ = _upsert(db, City, "slug", row["slug"], CITY_FIELDS, row)
        cities[row["slug"]] = obj
        counts["cities"] += 1
    sports = {}
    for row in data["sports"]:
        obj, _ = _upsert(db, Sport, "slug", row["slug"], SPORT_FIELDS, row)
        sports[row["slug"]] = obj
        counts["sports"] += 1
    db.flush()

    for row in data["events"]:
        event, created = _upsert(db, Event, "slug", row["slug"], EVENT_FIELDS, row)
        event.sport = sports[row["sport"]]
        event.city = cities[row["city"]]
        event.lat = row.get("lat") or event.city.lat
        event.lon = row.get("lon") or event.city.lon
        event.start_date = _d(row["start_date"])
        event.end_date = _d(row["end_date"])
        event.date_status = row.get("date_status", "confirmed")
        event.last_edition_date = _d(row.get("last_edition_date"))
        event.registration_opens = _d(row.get("registration_opens"))
        event.registration_closes = _d(row.get("registration_closes"))
        counts["created_events"] += int(created)
        counts["events"] += 1
        db.flush()

        existing = {c.name: c for c in event.categories}
        keep = set()
        for i, crow in enumerate(row["categories"]):
            cat = existing.get(crow["name"])
            if cat is None:
                cat = EventCategory(name=crow["name"])
                event.categories.append(cat)
            cat.sort_order = i
            for f in CATEGORY_FIELDS:
                setattr(cat, f, crow.get(f))
            cat.level = crow.get("level") or "open"
            keep.add(crow["name"])
            counts["categories"] += 1
        for name, cat in existing.items():
            if name in keep:
                continue
            in_use = db.scalar(select(Registration.id).where(Registration.category_id == cat.id).limit(1))
            if in_use is None:
                event.categories.remove(cat)
    db.commit()
    return counts


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    data = read_data()
    problems = validate(data)
    if problems:
        for p in problems:
            log.error("seed: %s", p)
        return 1
    if "--check" in argv:
        log.info(
            "seed data OK: %d cities, %d sports, %d events",
            len(data["cities"]),
            len(data["sports"]),
            len(data["events"]),
        )
        return 0
    with engine.connect() as conn:
        is_pg = conn.dialect.name == "postgresql"
        if is_pg:
            # several replicas start at once; only one seeds at a time
            conn.execute(text(f"SELECT pg_advisory_lock({SEED_LOCK_ID})"))
            conn.commit()
        try:
            with SessionLocal() as db:
                counts = load(db, data)
        finally:
            if is_pg:
                conn.execute(text(f"SELECT pg_advisory_unlock({SEED_LOCK_ID})"))
                conn.commit()
    log.info(
        "seeded %d cities, %d sports, %d events (%d new), %d categories",
        counts["cities"],
        counts["sports"],
        counts["events"],
        counts["created_events"],
        counts["categories"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
