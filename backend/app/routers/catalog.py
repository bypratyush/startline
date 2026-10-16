from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_sport
from ..models import City, Event, Sport
from ..serializers import city_out, event_card, sport_out

router = APIRouter(prefix="/api", tags=["catalogue"])


@router.get("/cities")
def list_cities(db: Session = Depends(get_db)):
    today = settings.today()
    counts = dict(
        db.execute(
            select(Event.city_id, func.count(Event.id)).where(Event.end_date >= today).group_by(Event.city_id)
        ).all()
    )
    cities = db.scalars(select(City).order_by(City.tier, City.name)).all()
    return [{**city_out(c), "events": counts.get(c.id, 0)} for c in cities]


@router.get("/sports")
def list_sports(db: Session = Depends(get_db)):
    today = settings.today()
    counts = dict(
        db.execute(
            select(Event.sport_id, func.count(Event.id)).where(Event.end_date >= today).group_by(Event.sport_id)
        ).all()
    )
    sports = db.scalars(select(Sport).order_by(Sport.sort_order)).all()
    return [{**sport_out(s), "events": counts.get(s.id, 0)} for s in sports]


@router.get("/sports/{slug}")
def sport_detail(slug: str, db: Session = Depends(get_db)):
    today = settings.today()
    sport = get_sport(db, slug)
    events = db.scalars(
        select(Event).where(Event.sport_id == sport.id, Event.end_date >= today).order_by(Event.start_date)
    ).all()
    return {**sport_out(sport, full=True), "events": [event_card(e, today) for e in events]}
