"""In-process cache of the event catalogue for the discovery endpoint.

The catalogue only changes when the seed runs, but /api/events is the hottest
endpoint and used to rebuild 215 events and ~800 categories through the ORM on
every request (about 400k Python calls). Under the registration-rush load test
that made a CPU-limited pod slow enough to fail its readiness probe.

Now each replica keeps fully loaded, detached Event objects plus their base
card JSON for CACHE_SECONDS, and a request only adds the per-athlete parts
(distance, match score, days until). Athlete data is never cached.
"""

import threading
import time
from datetime import date

from sqlalchemy import select

from .db import SessionLocal
from .models import Event
from .serializers import event_card

CACHE_SECONDS = 60

_lock = threading.Lock()
_state: dict = {"loaded_at": 0.0, "today": None, "rows": []}


def upcoming_events(today: date) -> list[tuple[Event, dict]]:
    """[(event, base_card)] for events that have not finished, in date order."""
    now = time.monotonic()
    if _state["today"] == today and now - _state["loaded_at"] < CACHE_SECONDS:
        return _state["rows"]
    with _lock:
        if _state["today"] == today and time.monotonic() - _state["loaded_at"] < CACHE_SECONDS:
            return _state["rows"]
        # its own short session: the objects outlive it, detached and read-only
        with SessionLocal() as db:
            events = db.scalars(
                select(Event).where(Event.end_date >= today).order_by(Event.start_date, Event.name)
            ).all()
            for e in events:
                # touch every relationship so nothing lazy-loads after the session closes
                _ = (e.sport.slug, e.city.slug, [c.name for c in e.categories])
            db.expunge_all()
        rows = [(e, event_card(e, today)) for e in events]
        _state.update(loaded_at=time.monotonic(), today=today, rows=rows)
        return rows


def invalidate() -> None:
    _state["loaded_at"] = 0.0
