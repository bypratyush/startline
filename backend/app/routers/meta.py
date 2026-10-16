from datetime import timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..models import Athlete, City, Event, ReadinessCheck, Registration, Sport
from ..observability import DB_UP

router = APIRouter()


@router.get("/", tags=["meta"])
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "metrics": "/metrics",
    }


@router.get("/health", tags=["meta"])
def health():
    """Liveness: the process is up and answering. Deliberately does not touch the DB."""
    return {"status": "ok"}


@router.get("/ready", tags=["meta"])
def ready(db: Session = Depends(get_db)):
    """Readiness: can this replica serve traffic? Needs the DB and the seeded catalogue."""
    try:
        sports = db.scalar(select(func.count()).select_from(Sport))
        events = db.scalar(select(func.count()).select_from(Event))
    except Exception as exc:  # noqa: BLE001 - any DB failure means not ready
        DB_UP.set(0)
        return JSONResponse(status_code=503, content={"status": "not-ready", "reason": type(exc).__name__})
    DB_UP.set(1)
    if not sports or not events:
        return JSONResponse(status_code=503, content={"status": "not-ready", "reason": "catalogue not seeded"})
    return {"status": "ready", "sports": sports, "events": events}


@router.get("/api/stats", tags=["meta"])
def stats(db: Session = Depends(get_db)):
    today = settings.today()
    upcoming = select(Event).where(Event.end_date >= today)
    by_sport = db.execute(
        select(Sport.slug, Sport.name, Sport.color, func.count(Event.id))
        .join(Event, Event.sport_id == Sport.id)
        .where(Event.end_date >= today)
        .group_by(Sport.slug, Sport.name, Sport.color, Sport.sort_order)
        .order_by(Sport.sort_order)
    ).all()
    by_tier = db.execute(
        select(City.tier, func.count(Event.id))
        .join(Event, Event.city_id == City.id)
        .where(Event.end_date >= today)
        .group_by(City.tier)
    ).all()
    cities_with_events = db.scalar(select(func.count(func.distinct(Event.city_id))).where(Event.end_date >= today))
    return {
        "today": today.isoformat(),
        "events_upcoming": db.scalar(select(func.count()).select_from(upcoming.subquery())),
        "events_next_30_days": db.scalar(
            select(func.count())
            .select_from(Event)
            .where(Event.start_date >= today, Event.start_date <= today + timedelta(days=30))
        ),
        "cities": db.scalar(select(func.count()).select_from(City)),
        "cities_with_events": cities_with_events,
        "sports": db.scalar(select(func.count()).select_from(Sport)),
        "athletes": db.scalar(select(func.count()).select_from(Athlete)),
        "registrations": db.scalar(
            select(func.count()).select_from(Registration).where(Registration.status == "confirmed")
        ),
        "readiness_checks": db.scalar(select(func.count()).select_from(ReadinessCheck)),
        "by_sport": [{"slug": s, "name": n, "color": c, "events": k} for s, n, c, k in by_sport],
        "by_tier": {f"tier_{t}": k for t, k in by_tier},
    }
