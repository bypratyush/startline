"""JSON logging and Prometheus metrics.

HTTP metrics (request count, latency by handler) come from
prometheus-fastapi-instrumentator. The counters below are business metrics:
what athletes actually do on the platform.
"""

import json
import logging
import sys
import time

from prometheus_client import Counter, Gauge, Histogram

REGISTRATIONS = Counter(
    "startline_registrations_total",
    "Event registrations created",
    ["sport", "city_tier"],
)
CANCELLATIONS = Counter("startline_registration_cancellations_total", "Registrations cancelled", ["sport"])
READINESS_CHECKS = Counter(
    "startline_readiness_checks_total",
    "Readiness calculations run",
    ["sport", "verdict"],
)
READINESS_SCORE = Histogram(
    "startline_readiness_score",
    "Distribution of readiness scores",
    ["sport"],
    buckets=(20, 40, 60, 80, 100),
)
EVENT_SEARCHES = Counter(
    "startline_event_searches_total",
    "Event list requests",
    ["recommendations"],
)
PROFILES = Counter("startline_profiles_created_total", "Athlete profiles created")
RECOMMEND_SECONDS = Histogram(
    "startline_recommendation_seconds",
    "Time spent scoring events for one request",
    buckets=(0.001, 0.0025, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25),
)
DB_UP = Gauge("startline_db_up", "1 if the last readiness probe reached the database")
EVENTS_LOADED = Gauge("startline_events_upcoming", "Upcoming events in the catalogue", ["sport"])


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            entry.update(extra)
        return json.dumps(entry)


def setup_logging(level: str) -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    logging.getLogger("uvicorn.access").disabled = True
    return logging.getLogger("startline")
