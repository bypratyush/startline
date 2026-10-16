from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_athlete, get_city, get_event, get_sport
from ..engine.profile import ProfileError, build_profile, validate_answers
from ..engine.season import season_plan
from ..models import Athlete, AthleteSport, ReadinessCheck, Registration, SavedEvent
from ..observability import PROFILES
from ..schemas import AthleteIn, AthletePatch, SaveIn
from ..serializers import athlete_out, event_card, registration_out

router = APIRouter(prefix="/api/athletes", tags=["athletes"])


def _apply_sports(db: Session, athlete: Athlete, body: AthleteIn) -> None:
    new = []
    for item in body.sports:
        sport = get_sport(db, item.sport)
        try:
            answers = validate_answers(sport, item.answers)
        except ProfileError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        level = build_profile(sport, answers).level
        new.append(AthleteSport(sport_id=sport.id, sport=sport, level=level, answers=answers))
    athlete.sports.clear()
    db.flush()
    athlete.sports.extend(new)


@router.post("", status_code=201)
def create_athlete(body: AthleteIn, db: Session = Depends(get_db)):
    city = get_city(db, body.city)
    athlete = Athlete(
        name=body.name,
        email=body.email,
        city_id=city.id,
        city=city,
        recommendations_enabled=body.recommendations_enabled,
    )
    db.add(athlete)
    _apply_sports(db, athlete, body)
    db.commit()
    db.refresh(athlete)
    PROFILES.inc()
    return athlete_out(athlete)


@router.get("/{athlete_id}")
def read_athlete(athlete_id: str, db: Session = Depends(get_db)):
    return athlete_out(get_athlete(db, athlete_id))


@router.put("/{athlete_id}")
def replace_athlete(athlete_id: str, body: AthleteIn, db: Session = Depends(get_db)):
    athlete = get_athlete(db, athlete_id)
    city = get_city(db, body.city)
    athlete.name = body.name
    athlete.email = body.email
    athlete.city_id = city.id
    athlete.city = city
    athlete.recommendations_enabled = body.recommendations_enabled
    _apply_sports(db, athlete, body)
    db.commit()
    db.refresh(athlete)
    return athlete_out(athlete)


@router.patch("/{athlete_id}")
def update_athlete(athlete_id: str, body: AthletePatch, db: Session = Depends(get_db)):
    athlete = get_athlete(db, athlete_id)
    if body.name is not None:
        athlete.name = body.name.strip()
    if body.email is not None:
        athlete.email = body.email
    if body.city is not None:
        city = get_city(db, body.city)
        athlete.city_id = city.id
        athlete.city = city
    if body.recommendations_enabled is not None:
        athlete.recommendations_enabled = body.recommendations_enabled
    db.commit()
    db.refresh(athlete)
    return athlete_out(athlete)


@router.delete("/{athlete_id}", status_code=204)
def delete_athlete(athlete_id: str, db: Session = Depends(get_db)):
    athlete = get_athlete(db, athlete_id)
    db.delete(athlete)
    db.commit()
    return Response(status_code=204)


@router.get("/{athlete_id}/saved")
def list_saved(athlete_id: str, db: Session = Depends(get_db)):
    get_athlete(db, athlete_id)
    today = settings.today()
    rows = db.scalars(
        select(SavedEvent).where(SavedEvent.athlete_id == athlete_id).order_by(SavedEvent.created_at.desc())
    ).all()
    return [event_card(r.event, today) for r in rows]


@router.post("/{athlete_id}/saved", status_code=201)
def save_event(athlete_id: str, body: SaveIn, db: Session = Depends(get_db)):
    get_athlete(db, athlete_id)
    event = get_event(db, body.event)
    if db.get(SavedEvent, (athlete_id, event.id)) is None:
        db.add(SavedEvent(athlete_id=athlete_id, event_id=event.id))
        db.commit()
    return {"saved": True, "event": event.slug}


@router.delete("/{athlete_id}/saved/{slug}")
def unsave_event(athlete_id: str, slug: str, db: Session = Depends(get_db)):
    get_athlete(db, athlete_id)
    event = get_event(db, slug)
    row = db.get(SavedEvent, (athlete_id, event.id))
    if row is not None:
        db.delete(row)
        db.commit()
    return {"saved": False, "event": event.slug}


@router.get("/{athlete_id}/registrations")
def list_registrations(athlete_id: str, db: Session = Depends(get_db)):
    get_athlete(db, athlete_id)
    rows = db.scalars(
        select(Registration).where(Registration.athlete_id == athlete_id).order_by(Registration.created_at.desc())
    ).all()
    return [registration_out(r) for r in rows]


@router.get("/{athlete_id}/season")
def season(athlete_id: str, db: Session = Depends(get_db)):
    """Registered and saved events in date order, with recovery-gap warnings."""
    athlete = get_athlete(db, athlete_id)
    today = settings.today()
    regs = db.scalars(
        select(Registration).where(Registration.athlete_id == athlete.id, Registration.status == "confirmed")
    ).all()
    saved = db.scalars(select(SavedEvent).where(SavedEvent.athlete_id == athlete.id)).all()
    registered_ids = {r.event_id for r in regs}
    entries = [{"kind": "registered", "event": r.event, "category": r.category, "registration": r} for r in regs]
    entries += [
        {"kind": "saved", "event": s.event, "category": s.event.categories[0] if s.event.categories else None}
        for s in saved
        if s.event_id not in registered_ids
    ]
    plan = season_plan(entries, today)
    checks = db.scalars(
        select(ReadinessCheck)
        .where(ReadinessCheck.athlete_id == athlete.id)
        .order_by(ReadinessCheck.created_at.desc())
        .limit(20)
    ).all()
    latest: dict[int, ReadinessCheck] = {}
    for c in checks:
        latest.setdefault(c.event_id, c)
    timeline = []
    for e in sorted(entries, key=lambda x: x["event"].start_date):
        if e["event"].end_date < today:
            continue
        rc = latest.get(e["event"].id)
        timeline.append(
            {
                "kind": e["kind"],
                "event": event_card(e["event"], today),
                "category": None if e["category"] is None else {"id": e["category"].id, "name": e["category"].name},
                "registration": registration_out(e["registration"]) if e.get("registration") else None,
                "readiness": None
                if rc is None
                else {
                    "score": rc.score,
                    "verdict": rc.verdict,
                    "category": rc.category.name,
                    "checked_at": rc.created_at.isoformat(),
                },
            }
        )
    return {"timeline": timeline, **plan}
