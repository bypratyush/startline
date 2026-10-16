from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_athlete, get_event
from ..engine.categories import age_bracket, is_doubles, is_team_entry
from ..models import Registration
from ..observability import CANCELLATIONS, REGISTRATIONS
from ..schemas import RegistrationIn
from ..serializers import registration_out

router = APIRouter(prefix="/api/registrations", tags=["registrations"])

BIB_START = 1001


def _age_on(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


@router.post("", status_code=201)
def register(body: RegistrationIn, db: Session = Depends(get_db)):
    today = settings.today()
    athlete = get_athlete(db, body.athlete_id)
    event = get_event(db, body.event)
    if event.start_date < today:
        raise HTTPException(status_code=409, detail="This event has already taken place")
    if event.registration_status == "closed":
        raise HTTPException(status_code=409, detail="Registration is closed for this event")
    cat = next((c for c in event.categories if c.id == body.category_id), None)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found for this event")

    age = _age_on(body.date_of_birth, event.start_date)
    if age < 5 or age > 100:
        raise HTTPException(status_code=422, detail="Please check the date of birth")
    lo, hi = age_bracket(cat)
    if lo and age < lo:
        raise HTTPException(status_code=422, detail=f"{cat.name} is open to athletes aged {lo} and over on race day")
    if hi and age >= hi:
        raise HTTPException(status_code=422, detail=f"{cat.name} is for athletes under {hi}")
    if is_doubles(cat) and not (body.partner_name or "").strip():
        raise HTTPException(status_code=422, detail="Doubles entries need your partner's name")
    if is_team_entry(cat, event.sport.family) and not (body.team_name or "").strip():
        raise HTTPException(status_code=422, detail="Team entries need a team name")

    existing = db.scalar(
        select(Registration).where(
            Registration.athlete_id == athlete.id,
            Registration.category_id == cat.id,
            Registration.status == "confirmed",
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail=f"You are already registered ({existing.code})")

    for _ in range(5):
        bib = (
            db.scalar(select(func.max(Registration.bib_number)).where(Registration.event_id == event.id))
            or BIB_START - 1
        ) + 1
        reg = Registration(
            code=f"SL{event.id:03d}-{bib}",
            bib_number=bib,
            athlete_id=athlete.id,
            event_id=event.id,
            category_id=cat.id,
            full_name=body.full_name.strip(),
            email=str(body.email),
            phone=body.phone,
            gender=body.gender,
            date_of_birth=body.date_of_birth,
            tshirt_size=body.tshirt_size,
            blood_group=body.blood_group,
            emergency_name=body.emergency_name.strip(),
            emergency_phone=body.emergency_phone,
            team_name=(body.team_name or "").strip() or None,
            partner_name=(body.partner_name or "").strip() or None,
        )
        db.add(reg)
        try:
            db.commit()
            break
        except IntegrityError:
            # two registrations raced for the same bib number: take the next one
            db.rollback()
    else:
        raise HTTPException(status_code=503, detail="Could not allocate a bib number, please retry")
    db.refresh(reg)
    REGISTRATIONS.labels(sport=event.sport.slug, city_tier=str(event.city.tier)).inc()
    return registration_out(reg)


@router.get("/{code}")
def read_registration(code: str, db: Session = Depends(get_db)):
    reg = db.scalar(select(Registration).where(Registration.code == code))
    if reg is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    return registration_out(reg)


@router.delete("/{code}")
def cancel_registration(code: str, athlete_id: str, db: Session = Depends(get_db)):
    reg = db.scalar(select(Registration).where(Registration.code == code))
    if reg is None or reg.athlete_id != athlete_id:
        raise HTTPException(status_code=404, detail="Registration not found")
    if reg.status != "cancelled":
        reg.status = "cancelled"
        db.commit()
        CANCELLATIONS.labels(sport=reg.event.sport.slug).inc()
    return registration_out(reg)
