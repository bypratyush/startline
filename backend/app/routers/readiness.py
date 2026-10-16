from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import get_athlete, get_event
from ..engine.readiness import ReadinessError, assess
from ..models import ReadinessCheck
from ..observability import READINESS_CHECKS, READINESS_SCORE
from ..schemas import ReadinessIn
from ..serializers import category_out

router = APIRouter(prefix="/api/readiness", tags=["readiness"])


@router.post("")
def check_readiness(body: ReadinessIn, db: Session = Depends(get_db)):
    today = settings.today()
    event = get_event(db, body.event)
    cat = next((c for c in event.categories if c.id == body.category_id), None)
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found for this event")
    athlete = get_athlete(db, body.athlete_id, required=False) if body.athlete_id else None
    try:
        result = assess(event, cat, dict(body.inputs), today)
    except ReadinessError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    db.add(
        ReadinessCheck(
            athlete_id=athlete.id if athlete else None,
            event_id=event.id,
            category_id=cat.id,
            inputs=result["inputs"],
            score=result["score"],
            verdict=result["verdict"],
        )
    )
    db.commit()
    READINESS_CHECKS.labels(sport=event.sport.slug, verdict=result["verdict"]).inc()
    READINESS_SCORE.labels(sport=event.sport.slug).observe(result["score"])
    return {"event": event.slug, "category": category_out(cat), **result}
