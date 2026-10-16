"""Model -> JSON shapes used by the API (and by the React app)."""

from datetime import date


def city_out(c, brief: bool = False) -> dict:
    out = {"slug": c.slug, "name": c.name, "state": c.state, "tier": c.tier, "lat": c.lat, "lon": c.lon}
    if not brief:
        out.update({"sports_note": c.sports_note, "air_quality_note": c.air_quality_note})
    return out


def sport_brief(s) -> dict:
    return {"slug": s.slug, "name": s.name, "family": s.family, "color": s.color}


def sport_out(s, full: bool = False) -> dict:
    out = {
        **sport_brief(s),
        "tagline": s.tagline,
        "description": s.description,
        "questions": s.questions,
        "level_definitions": s.level_definitions,
        "disciplines": s.disciplines,
    }
    if full:
        out.update(
            {
                "recommendation_rules": s.recommendation_rules,
                "guide": s.guide,
                "sources": s.sources,
            }
        )
    return out


def category_out(c) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "distance_km": c.distance_km,
        "swim_km": c.swim_km,
        "bike_km": c.bike_km,
        "run_km": c.run_km,
        "fee_inr": c.fee_inr,
        "start_time": c.start_time,
        "cutoff_minutes": c.cutoff_minutes,
        "min_age": c.min_age,
        "level": c.level,
        "eligibility": c.eligibility,
        "notes": c.notes,
    }


def _fees(e) -> tuple[int | None, int | None]:
    fees = [c.fee_inr for c in e.categories if c.fee_inr]
    return (min(fees), max(fees)) if fees else (None, None)


def event_card(e, today: date, match=None, distance_km: float | None = None) -> dict:
    fee_min, fee_max = _fees(e)
    return {
        "slug": e.slug,
        "name": e.name,
        "edition": e.edition,
        "sport": sport_brief(e.sport),
        "discipline": e.discipline,
        "city": city_out(e.city, brief=True),
        "venue": e.venue,
        "start_date": e.start_date.isoformat(),
        "end_date": e.end_date.isoformat(),
        "date_status": e.date_status,
        "days_until": (e.start_date - today).days,
        "distance_km": None if distance_km is None else round(distance_km),
        "categories": [
            {"id": c.id, "name": c.name, "distance_km": c.distance_km, "level": c.level, "fee_inr": c.fee_inr}
            for c in e.categories
        ],
        "fee_min": fee_min,
        "fee_max": fee_max,
        "registration_status": e.registration_status,
        "registration_closes": e.registration_closes.isoformat() if e.registration_closes else None,
        "beginner_friendly": e.beginner_friendly,
        "profile": (e.course or {}).get("profile"),
        "terrain": (e.course or {}).get("terrain"),
        "tags": e.tags or [],
        "match": match.as_dict() if match else None,
    }


def event_detail(e, today: date, match=None, distance_km: float | None = None, spots_taken: int = 0) -> dict:
    out = event_card(e, today, match, distance_km)
    out.update(
        {
            "summary": e.summary,
            "organiser": e.organiser,
            "official_url": e.official_url,
            "last_edition_date": e.last_edition_date.isoformat() if e.last_edition_date else None,
            "registration": {
                "status": e.registration_status,
                "opens": e.registration_opens.isoformat() if e.registration_opens else None,
                "closes": e.registration_closes.isoformat() if e.registration_closes else None,
                "url": e.registration_url,
                "notes": e.registration_notes,
            },
            "course": e.course or {},
            "format": e.format,
            "highlights": e.highlights or [],
            "amenities": e.amenities or [],
            "lat": e.lat,
            "lon": e.lon,
            "categories": [category_out(c) for c in e.categories],
            "sources": e.sources or [],
            "registrations_count": spots_taken,
            "city": city_out(e.city),
        }
    )
    return out


def athlete_out(a) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "email": a.email,
        "city": city_out(a.city, brief=True) if a.city else None,
        "recommendations_enabled": a.recommendations_enabled,
        "sports": [
            {
                "sport": sport_brief(s.sport),
                "level": s.level,
                "answers": s.answers,
                "labels": _labels(s.sport, s.answers),
            }
            for s in sorted(a.sports, key=lambda s: s.sport.sort_order)
        ],
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _labels(sport, answers: dict) -> list[dict]:
    out = []
    for q in sport.questions:
        val = answers.get(q["id"])
        opt = next((o for o in q["options"] if o["value"] == val), None)
        if opt:
            out.append({"question": q.get("short") or q["prompt"], "answer": opt["label"]})
    return out


def registration_out(r) -> dict:
    return {
        "code": r.code,
        "bib_number": r.bib_number,
        "status": r.status,
        "event": {
            "slug": r.event.slug,
            "name": r.event.name,
            "start_date": r.event.start_date.isoformat(),
            "date_status": r.event.date_status,
            "city": r.event.city.name,
            "venue": r.event.venue,
            "sport": sport_brief(r.event.sport),
            "official_url": r.event.official_url,
        },
        "category": {
            "id": r.category.id,
            "name": r.category.name,
            "start_time": r.category.start_time,
            "fee_inr": r.category.fee_inr,
        },
        "full_name": r.full_name,
        "email": r.email,
        "phone": r.phone,
        "team_name": r.team_name,
        "partner_name": r.partner_name,
        "tshirt_size": r.tshirt_size,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
