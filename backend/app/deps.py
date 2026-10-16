from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .engine.profile import SportProfile, build_profile
from .models import Athlete, City, Event, Sport


def get_event(db: Session, slug: str) -> Event:
    event = db.scalar(select(Event).where(Event.slug == slug))
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def get_city(db: Session, slug: str) -> City:
    city = db.scalar(select(City).where(City.slug == slug))
    if city is None:
        raise HTTPException(status_code=404, detail=f"Unknown city '{slug}'")
    return city


def get_sport(db: Session, slug: str) -> Sport:
    sport = db.scalar(select(Sport).where(Sport.slug == slug))
    if sport is None:
        raise HTTPException(status_code=404, detail=f"Unknown sport '{slug}'")
    return sport


def get_athlete(db: Session, athlete_id: str | None, required: bool = True) -> Athlete | None:
    if not athlete_id:
        if required:
            raise HTTPException(status_code=404, detail="Athlete not found")
        return None
    athlete = db.get(Athlete, athlete_id)
    if athlete is None and required:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete


def athlete_profiles(athlete: Athlete | None) -> dict[str, SportProfile]:
    if athlete is None:
        return {}
    return {s.sport.slug: build_profile(s.sport, s.answers) for s in athlete.sports}
