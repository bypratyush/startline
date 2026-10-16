import time
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..catalog_cache import upcoming_events
from ..config import settings
from ..db import get_db
from ..deps import athlete_profiles, get_athlete, get_city, get_event
from ..engine.geo import haversine_km
from ..engine.guide import build_guide, weather_card
from ..engine.readiness import form_for
from ..engine.recommend import RECOMMEND_THRESHOLD, score_event
from ..models import Event, Registration, Sport
from ..observability import EVENT_SEARCHES, RECOMMEND_SECONDS
from ..serializers import event_card, event_detail

router = APIRouter(prefix="/api/events", tags=["events"])


def _split(values: list[str]) -> list[str]:
    out = []
    for v in values:
        out.extend(p.strip() for p in v.split(",") if p.strip())
    return out


def _month_bounds(month: str) -> tuple[date, date]:
    y, m = (int(p) for p in month.split("-"))
    start = date(y, m, 1)
    end = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
    return start, end


def _matches_text(e: Event, q: str) -> bool:
    hay = " ".join(
        filter(None, [e.name, e.venue, e.city.name, e.city.state, e.sport.name, e.discipline, " ".join(e.tags or [])])
    ).lower()
    return all(word in hay for word in q.lower().split())


@router.get("")
def list_events(
    sport: list[str] = Query(default=[], description="sport slugs, repeat or comma-separate"),
    city: str | None = Query(default=None, description="city slug to measure distance from"),
    radius_km: int | None = Query(default=None, ge=1, le=5000),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    level: Literal["beginner", "intermediate", "advanced"] | None = None,
    registration: Literal["open", "upcoming"] | None = None,
    beginner_friendly: bool | None = None,
    q: str | None = Query(default=None, max_length=80),
    sort: Literal["recommended", "date", "distance"] = "recommended",
    athlete_id: str | None = None,
    recommend: bool = True,
    limit: int = Query(default=300, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    today = settings.today()
    slugs = _split(sport)
    athlete = get_athlete(db, athlete_id, required=False)
    origin = get_city(db, city) if city else (athlete.city if athlete else None)
    # Everything below works on the cached catalogue and already-loaded objects, so
    # hand the connection back to the pool before the CPU-heavy scoring starts.
    db.commit()

    # filters that apply before the sport facet is counted
    rows = []
    bases = {}
    for e, base in upcoming_events(today):
        bases[e.id] = base
        dist = haversine_km(origin.lat, origin.lon, e.lat, e.lon) if origin else None
        if radius_km and dist is not None and dist > radius_km:
            continue
        if q and not _matches_text(e, q):
            continue
        if month:
            lo, hi = _month_bounds(month)
            if not (lo <= e.start_date <= hi):
                continue
        if level and not any(c.level in (level, "open") for c in e.categories):
            continue
        if registration and e.registration_status != registration:
            continue
        if beginner_friendly and not e.beginner_friendly:
            continue
        rows.append((e, dist))

    sport_facet: dict[str, int] = {}
    for e, _ in rows:
        sport_facet[e.sport.slug] = sport_facet.get(e.sport.slug, 0) + 1
    if slugs:
        rows = [(e, d) for e, d in rows if e.sport.slug in slugs]
    month_facet: dict[str, int] = {}
    for e, _ in rows:
        key = e.start_date.strftime("%Y-%m")
        month_facet[key] = month_facet.get(key, 0) + 1

    # recommendations
    if athlete is None:
        mode = "no-profile"
    elif not athlete.recommendations_enabled or not recommend:
        mode = "off"
    else:
        mode = "on"
    profiles = athlete_profiles(athlete) if mode == "on" else {}
    t0 = time.perf_counter()
    scored = []
    for e, dist in rows:
        m = score_event(e, profiles.get(e.sport.slug), origin, today) if profiles else None
        scored.append((e, dist, m))
    RECOMMEND_SECONDS.observe(time.perf_counter() - t0)
    EVENT_SEARCHES.labels(recommendations=mode).inc()

    def is_rec(m):
        return m is not None and m.score >= RECOMMEND_THRESHOLD

    if sort == "recommended" and mode == "on":
        scored.sort(key=lambda r: (not is_rec(r[2]), -(r[2].score if is_rec(r[2]) else 0), r[0].start_date))
    elif sort == "distance" and origin:
        scored.sort(key=lambda r: (r[1] if r[1] is not None else 1e9, r[0].start_date))
    # default: already ordered by date

    recommended_count = sum(1 for r in scored if is_rec(r[2]))
    page = scored[offset : offset + limit]
    return {
        "total": len(scored),
        "recommendations": mode,
        "recommended_count": recommended_count,
        "origin": None if origin is None else {"slug": origin.slug, "name": origin.name},
        "facets": {"sports": sport_facet, "months": dict(sorted(month_facet.items()))},
        "items": [
            {
                **bases[e.id],
                "distance_km": None if dist is None else round(dist),
                "match": m.as_dict() if is_rec(m) else None,
                "recommended": is_rec(m),
            }
            for e, dist, m in page
        ],
    }


@router.get("/{slug}")
def get_event_detail(slug: str, athlete_id: str | None = None, db: Session = Depends(get_db)):
    today = settings.today()
    event = get_event(db, slug)
    athlete = get_athlete(db, athlete_id, required=False)
    origin = athlete.city if athlete else None
    dist = haversine_km(origin.lat, origin.lon, event.lat, event.lon) if origin else None
    match = None
    if athlete and athlete.recommendations_enabled:
        match = score_event(event, athlete_profiles(athlete).get(event.sport.slug), origin, today)
    taken = db.scalar(
        select(func.count())
        .select_from(Registration)
        .where(Registration.event_id == event.id, Registration.status == "confirmed")
    )
    out = event_detail(event, today, match, dist, taken)
    first_start = next((c.start_time for c in event.categories if c.start_time), None)
    out["weather"] = weather_card(event.city, event.start_date, first_start)
    out["sport"] = {**out["sport"], "level_definitions": event.sport.level_definitions}
    # other upcoming events in the same sport nearby, for "you might also like"
    others = db.scalars(
        select(Event)
        .join(Sport)
        .where(Event.sport_id == event.sport_id, Event.id != event.id, Event.end_date >= today)
        .order_by(Event.start_date)
    ).all()
    others.sort(key=lambda e: haversine_km(event.lat, event.lon, e.lat, e.lon))
    out["related"] = [event_card(e, today) for e in others[:4]]
    return out


@router.get("/{slug}/guide")
def get_guide(slug: str, category_id: int | None = None, db: Session = Depends(get_db)):
    event = get_event(db, slug)
    cat = None
    if category_id is not None:
        cat = next((c for c in event.categories if c.id == category_id), None)
        if cat is None:
            raise HTTPException(status_code=404, detail="Category not found for this event")
    return build_guide(event, cat)


@router.get("/{slug}/readiness-form")
def readiness_form(slug: str, athlete_id: str | None = None, db: Session = Depends(get_db)):
    event = get_event(db, slug)
    athlete = get_athlete(db, athlete_id, required=False)
    prefill = {}
    profile = athlete_profiles(athlete).get(event.sport.slug)
    if profile:
        prefill = {**profile.prefill, "level": profile.level}
    return {"sport": event.sport.slug, "has_profile": profile is not None, **form_for(event.sport, prefill)}


def _ics_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


@router.get("/{slug}/calendar.ics")
def calendar(slug: str, category_id: int | None = None, db: Session = Depends(get_db)):
    event = get_event(db, slug)
    cat = next((c for c in event.categories if c.id == category_id), None) if category_id else None
    cat = cat or next((c for c in event.categories if c.start_time), None)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//StartLine//Events//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{event.slug}-{cat.id if cat else 0}@startline",
        f"DTSTAMP:{stamp}",
    ]
    if cat and cat.start_time:
        h, m = (int(p) for p in cat.start_time.split(":"))
        ist = datetime(event.start_date.year, event.start_date.month, event.start_date.day, h, m)
        start_utc = ist - timedelta(hours=5, minutes=30)
        hours = max(1, (cat.cutoff_minutes or 180) // 60)
        lines += [
            f"DTSTART:{start_utc:%Y%m%dT%H%M%SZ}",
            f"DTEND:{start_utc + timedelta(hours=hours):%Y%m%dT%H%M%SZ}",
        ]
    else:
        lines += [
            f"DTSTART;VALUE=DATE:{event.start_date:%Y%m%d}",
            f"DTEND;VALUE=DATE:{event.end_date + timedelta(days=1):%Y%m%d}",
        ]
    title = event.name + (f" - {cat.name}" if cat else "")
    desc = (event.summary or "") + (
        " Date expected, confirm with the organiser." if event.date_status != "confirmed" else ""
    )
    lines += [
        f"SUMMARY:{_ics_escape(title)}",
        f"LOCATION:{_ics_escape((event.venue or '') + ', ' + event.city.name)}",
        f"DESCRIPTION:{_ics_escape(desc)}",
        f"GEO:{event.lat:.4f};{event.lon:.4f}",
    ]
    if event.official_url:
        lines.append(f"URL:{event.official_url}")
    lines += ["END:VEVENT", "END:VCALENDAR"]
    return Response(
        content="\r\n".join(lines) + "\r\n",
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{event.slug}.ics"'},
    )
