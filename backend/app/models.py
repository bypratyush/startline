"""Database tables.

Reference data (cities, sports, events, categories) is loaded by app.seed.
Athlete data (profiles, saved events, registrations, readiness checks) is
written by the API.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class City(Base):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(80))
    tier: Mapped[int] = mapped_column(Integer)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    elevation_m: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # {"max_c": [12], "min_c": [12], "rain_mm": [12], "humidity_pct": [12]}
    climate: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    air_quality_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    sports_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Sport(Base):
    __tablename__ = "sports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    family: Mapped[str] = mapped_column(String(20))  # run | ride | swim | tri | hyrox | ocr | court | team
    color: Mapped[str] = mapped_column(String(9))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    tagline: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    disciplines: Mapped[list] = mapped_column(JSON, default=list)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    level_definitions: Mapped[dict] = mapped_column(JSON, default=dict)
    recommendation_rules: Mapped[list] = mapped_column(JSON, default=list)
    guide: Mapped[dict] = mapped_column(JSON, default=dict)
    sources: Mapped[list] = mapped_column(JSON, default=list)


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    edition: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sport_id: Mapped[int] = mapped_column(ForeignKey("sports.id"), index=True)
    discipline: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), index=True)
    venue: Mapped[str | None] = mapped_column(String(240), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    start_date: Mapped[date] = mapped_column(Date, index=True)
    end_date: Mapped[date] = mapped_column(Date)
    date_status: Mapped[str] = mapped_column(String(12), default="confirmed")  # confirmed | expected
    last_edition_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    organiser: Mapped[str | None] = mapped_column(String(160), nullable=True)
    official_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    registration_status: Mapped[str] = mapped_column(String(12), default="unknown")
    registration_opens: Mapped[date | None] = mapped_column(Date, nullable=True)
    registration_closes: Mapped[date | None] = mapped_column(Date, nullable=True)
    registration_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    registration_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    course: Mapped[dict] = mapped_column(JSON, default=dict)
    format: Mapped[str | None] = mapped_column(Text, nullable=True)
    highlights: Mapped[list] = mapped_column(JSON, default=list)
    tips: Mapped[list] = mapped_column(JSON, default=list)
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    beginner_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    sources: Mapped[list] = mapped_column(JSON, default=list)

    sport: Mapped[Sport] = relationship(lazy="joined")
    city: Mapped[City] = relationship(lazy="joined")
    categories: Mapped[list["EventCategory"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventCategory.sort_order",
        lazy="selectin",
    )


class EventCategory(Base):
    __tablename__ = "event_categories"
    __table_args__ = (UniqueConstraint("event_id", "name", name="uq_category_event_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    swim_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    bike_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    run_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    fee_inr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    cutoff_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="open")
    eligibility: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    event: Mapped[Event] = relationship(back_populates="categories")


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True)
    recommendations_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    city: Mapped[City | None] = relationship(lazy="joined")
    sports: Mapped[list["AthleteSport"]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan", lazy="selectin"
    )


class AthleteSport(Base):
    __tablename__ = "athlete_sports"
    __table_args__ = (UniqueConstraint("athlete_id", "sport_id", name="uq_athlete_sport"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    sport_id: Mapped[int] = mapped_column(ForeignKey("sports.id"))
    level: Mapped[str] = mapped_column(String(16))
    answers: Mapped[dict] = mapped_column(JSON, default=dict)

    athlete: Mapped[Athlete] = relationship(back_populates="sports")
    sport: Mapped[Sport] = relationship(lazy="joined")


class SavedEvent(Base):
    __tablename__ = "saved_events"

    athlete_id: Mapped[str] = mapped_column(ForeignKey("athletes.id", ondelete="CASCADE"), primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    event: Mapped[Event] = relationship(lazy="joined")


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("event_id", "bib_number", name="uq_registration_bib"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    bib_number: Mapped[int] = mapped_column(Integer)
    athlete_id: Mapped[str] = mapped_column(ForeignKey("athletes.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("event_categories.id"))
    full_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(16))
    gender: Mapped[str] = mapped_column(String(12))
    date_of_birth: Mapped[date] = mapped_column(Date)
    tshirt_size: Mapped[str | None] = mapped_column(String(4), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(4), nullable=True)
    emergency_name: Mapped[str] = mapped_column(String(80))
    emergency_phone: Mapped[str] = mapped_column(String(16))
    team_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    partner_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="confirmed")  # confirmed | cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    event: Mapped[Event] = relationship(lazy="joined")
    category: Mapped[EventCategory] = relationship(lazy="joined")


class ReadinessCheck(Base):
    __tablename__ = "readiness_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[str | None] = mapped_column(
        ForeignKey("athletes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    category_id: Mapped[int] = mapped_column(ForeignKey("event_categories.id"))
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    score: Mapped[int] = mapped_column(Integer)
    verdict: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    event: Mapped[Event] = relationship(lazy="joined")
    category: Mapped[EventCategory] = relationship(lazy="joined")
