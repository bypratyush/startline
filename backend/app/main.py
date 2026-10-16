"""StartLine API.

GET  /                      service info
GET  /health  /ready        liveness and readiness probes
GET  /metrics               Prometheus metrics
GET  /api/cities  /api/sports  /api/sports/{slug}
GET  /api/events            discovery: filters, distance, recommendations
GET  /api/events/{slug}     detail, /guide, /readiness-form, /calendar.ics
POST /api/athletes          profile with 2-3 answers per sport
POST /api/readiness         readiness calculator
POST /api/registrations     register for an event category
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, select
from sqlalchemy.exc import TimeoutError as PoolTimeout

from .config import settings
from .db import SessionLocal, db_is_up
from .models import Event, Sport
from .observability import DB_UP, EVENTS_LOADED, setup_logging
from .routers import athletes, catalog, events, meta, readiness, registrations

log = setup_logging(settings.log_level)


def refresh_catalogue_gauge() -> None:
    try:
        with SessionLocal() as db:
            rows = db.execute(
                select(Sport.slug, func.count(Event.id))
                .join(Event, Event.sport_id == Sport.id, isouter=True)
                .where((Event.end_date >= settings.today()) | (Event.id.is_(None)))
                .group_by(Sport.slug)
            ).all()
        for slug, count in rows:
            EVENTS_LOADED.labels(sport=slug).set(count)
    except Exception as exc:  # noqa: BLE001 - the gauge is best effort
        log.warning("catalogue gauge not refreshed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("starting %s %s (%s)", settings.app_name, settings.app_version, settings.app_env)
    # a gauge starts at 0: set it from a real check so a fresh pod does not look like a DB outage
    DB_UP.set(1 if db_is_up() else 0)
    refresh_catalogue_gauge()
    yield
    logging.getLogger("startline").info("shutting down")


app = FastAPI(
    title="StartLine API",
    version=settings.app_version,
    description="Find sports events near you, check your readiness, read the guide and register.",
    # the schema lives under /api so the Ingress /api route serves it; Swagger UI stays at /docs
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(PoolTimeout)
async def pool_exhausted(request: Request, exc: PoolTimeout):
    # every DB connection of this replica is busy: shed load explicitly instead of a 500
    log.warning("db pool exhausted on %s", request.url.path)
    return JSONResponse(
        status_code=503, content={"detail": "StartLine is busy, please retry"}, headers={"Retry-After": "1"}
    )


for r in (meta, catalog, events, athletes, registrations, readiness):
    app.include_router(r.router)

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/metrics", "/health", "/ready"],
).instrument(app, metric_namespace="startline").expose(app, endpoint="/metrics", include_in_schema=False)
