"""Unit tests for the domain logic, independent of HTTP."""

from datetime import date
from types import SimpleNamespace as NS

import pytest

from app.engine.categories import age_bracket, category_formats, parse_duration, rating_bracket, tri_class
from app.engine.guide import heat_index_c
from app.engine.profile import build_profile
from app.engine.readiness import ReadinessError, _riegel, _weeks, assess
from app.engine.recommend import category_fit
from app.engine.season import recovery_days

TODAY = date(2026, 10, 15)


def cat(name="Open", **kw):
    base = dict(
        id=1,
        name=name,
        distance_km=None,
        swim_km=None,
        bike_km=None,
        run_km=None,
        fee_inr=None,
        start_time="06:00",
        cutoff_minutes=None,
        min_age=None,
        level="open",
        eligibility=None,
    )
    base.update(kw)
    return NS(**base)


def event(family, slug, cats, start=date(2027, 1, 17), **kw):
    sport = NS(slug=slug, family=family, name=slug.title())
    base = dict(
        sport=sport,
        categories=cats,
        start_date=start,
        end_date=start,
        course={},
        discipline=None,
        name=f"Test {slug}",
        beginner_friendly=False,
        registration_status="open",
        lat=12.97,
        lon=77.59,
    )
    base.update(kw)
    return NS(**base)


def sport_with(questions, slug="pickleball", family="court"):
    return NS(slug=slug, family=family, name=slug, questions=questions)


# ---------------------------------------------------------------- categories


def test_parse_duration():
    assert parse_duration("25:30") == 1530
    assert parse_duration("1:58:20") == 7100
    assert parse_duration("abc") is None


def test_age_brackets_from_category_names():
    assert age_bracket(cat("Men's Singles 45+")) == (45, None)
    assert age_bracket(cat("U-19 Boys")) == (None, 19)
    assert age_bracket(cat("1 km (ages 8-10)")) == (8, 11)
    assert age_bracket(cat("Kids Run")) == (None, 16)
    # eligibility text mentioning other age slabs is not an entry rule
    assert age_bracket(cat("Open 10K", min_age=15, eligibility="youth 15-21 and 65+ criteria")) == (15, None)


def test_rating_and_format_parsing():
    assert rating_bracket(cat("Mixed Doubles 3.5")) == (3.5, False)
    assert rating_bracket(cat("Men's Doubles 4.0+")) == (4.0, True)
    assert category_formats(cat("Mixed Doubles 3.5")) == {"mixed"}
    assert "7-a-side" in category_formats(cat("Open 7-a-side"))


def test_triathlon_distance_classes():
    assert tri_class(cat(swim_km=0.4, bike_km=10, run_km=2.5)) == 0
    assert tri_class(cat(swim_km=0.75, bike_km=20, run_km=5)) == 1
    assert tri_class(cat(swim_km=1.5, bike_km=40, run_km=10)) == 2
    assert tri_class(cat(swim_km=1.9, bike_km=90, run_km=21.1)) == 3
    assert tri_class(cat(swim_km=3.8, bike_km=180, run_km=42.2)) == 4


# ---------------------------------------------------------------- recommender

PB_QUESTIONS = [
    {
        "id": "rating",
        "kind": "rating",
        "options": [
            {"value": "3.5", "label": "3.5", "rating": 3.5, "level": "intermediate"},
            {"value": "4.0", "label": "4.0", "rating": 4.0, "level": "advanced"},
        ],
    },
    {
        "id": "fmt",
        "kind": "format",
        "options": [
            {"value": "doubles", "label": "Doubles", "formats": ["doubles"]},
            {"value": "singles", "label": "Singles", "formats": ["singles"]},
        ],
    },
]


def test_rated_draw_above_your_rating_is_ineligible():
    p = build_profile(sport_with(PB_QUESTIONS), {"rating": "4.0", "fmt": "doubles"})
    ev = event("court", "pickleball", [])
    fit = category_fit(ev, cat("Men's Doubles 3.5", level="intermediate"), p)
    assert fit.eligible is False
    good = category_fit(ev, cat("Men's Doubles 4.0", level="advanced"), p)
    assert good.eligible and good.fit > fit.fit


def test_preferred_format_wins():
    p = build_profile(sport_with(PB_QUESTIONS), {"rating": "3.5", "fmt": "doubles"})
    ev = event("court", "pickleball", [])
    doubles = category_fit(ev, cat("Mixed Doubles 3.5 and Doubles 3.5", level="intermediate"), p)
    singles = category_fit(ev, cat("Singles 3.5", level="intermediate"), p)
    assert doubles.fit > singles.fit


def test_kids_categories_are_never_picked_for_adults():
    swim_q = [
        {"id": "level", "kind": "level", "options": [{"value": "beginner", "label": "Beginner", "level": "beginner"}]}
    ]
    p = build_profile(sport_with(swim_q, "swimming", "swim"), {"level": "beginner"})
    ev = event("swim", "swimming", [])
    assert category_fit(ev, cat("1 km (ages 8-10)", distance_km=1, level="beginner"), p).eligible is False
    assert category_fit(ev, cat("1 km", distance_km=1, level="beginner"), p).eligible is True


def test_first_triathlon_wording():
    q = [
        {"id": "level", "kind": "level", "options": [{"value": "beginner", "label": "B", "level": "beginner"}]},
        {
            "id": "exp",
            "kind": "capacity",
            "applies_to": "tri_class",
            "options": [{"value": "none", "label": "None yet", "capacity": 0}],
        },
    ]
    p = build_profile(sport_with(q, "triathlon", "tri"), {"level": "beginner", "exp": "none"})
    fit = category_fit(
        event("tri", "triathlon", []), cat("Super Sprint", swim_km=0.4, bike_km=10, run_km=2.5, level="beginner"), p
    )
    assert any("first race" in r for r in fit.reasons)


# ---------------------------------------------------------------- readiness


def test_riegel_matches_published_formula():
    # 5K in 25:00 -> 10K = 1500 x 2^1.06 = 3127 s (52:07)
    assert round(_riegel(1500, 5, 10)) == 3127


def run_inputs(**kw):
    base = {"recent_distance": "10", "recent_time": "55:00", "longest_run_km": 18, "weekly_km": 35, "runs_per_week": 4}
    base.update(kw)
    return base


def test_trained_runner_is_ready_for_a_half():
    ev = event("run", "running", [], start=date(2027, 1, 17))
    half = cat("Half Marathon", distance_km=21.1, level="intermediate", cutoff_minutes=210)
    res = assess(ev, half, run_inputs(), TODAY)
    assert res["verdict"] == "ready"
    assert res["prediction"]["finish_seconds"] < 210 * 60
    assert res["plan"]["rows"][-1]["phase"] == "Race week"


def test_undertrained_runner_is_told_to_build_for_a_marathon():
    ev = event("run", "running", [], start=date(2026, 11, 15))
    full = cat("Marathon", distance_km=42.195, level="advanced", cutoff_minutes=360)
    res = assess(ev, full, run_inputs(longest_run_km=8, weekly_km=12, runs_per_week=2), TODAY)
    assert res["verdict"] in ("build", "not-this-one")
    assert res["gaps"]


def test_brevet_uses_acp_time_limit():
    ev = event("ride", "cycling", [], discipline="brevet")
    brm = cat("BRM 200", distance_km=200)
    res = assess(ev, brm, {"longest_ride_km": 150, "avg_speed_kmh": 24, "weekly_km": 200, "climb_m": 800}, TODAY)
    assert res["prediction"]["cutoff_label"] == "13:30:00"


def test_triathlon_splits_add_up():
    ev = event("tri", "triathlon", [])
    oly = cat("Olympic", swim_km=1.5, bike_km=40, run_km=10, level="intermediate")
    res = assess(
        ev,
        oly,
        {
            "swim_pace_100m": "2:15",
            "longest_swim_m": 1500,
            "bike_speed_kmh": 26,
            "longest_ride_km": 50,
            "run_10k_time": "55:00",
            "longest_run_km": 12,
            "open_water_swims": 3,
        },
        TODAY,
    )
    splits = res["prediction"]["splits"]
    assert {s["label"] for s in splits} == {"Swim", "T1 + T2", "Bike", "Run"}
    assert abs(sum(s["seconds"] for s in splits) - res["prediction"]["finish_seconds"]) <= 4


def test_court_readiness_reports_tournament_day_load():
    ev = event("court", "badminton", [])
    res = assess(
        ev,
        cat("Men's Doubles Open", level="advanced"),
        {
            "level": "intermediate",
            "sessions_per_week": 2,
            "matches_per_month": 4,
            "longest_play_min": 60,
            "years_playing": 3,
        },
        TODAY,
    )
    assert res["day_load"]["matches"] >= 2
    assert 0 <= res["score"] <= 100


def test_readiness_validates_inputs():
    ev = event("run", "running", [])
    with pytest.raises(ReadinessError):
        assess(ev, cat(distance_km=10), run_inputs(recent_time="fast"), TODAY)
    with pytest.raises(ReadinessError):
        assess(ev, cat(distance_km=10), run_inputs(weekly_km=9999), TODAY)


# ---------------------------------------------------------------- guide and season


def test_heat_index_matches_nws_table():
    # NWS chart: 90 F (32.2 C) at 70% relative humidity feels like 106 F (41.1 C)
    assert heat_index_c(32.2, 70) == pytest.approx(41.1, abs=0.8)
    # below about 27 C the index is close to the air temperature
    assert heat_index_c(20, 50) == pytest.approx(19.6, abs=1.0)


def test_recovery_days_scale_with_distance():
    run = event("run", "running", [])
    assert recovery_days(run, cat(distance_km=42.195)) > recovery_days(run, cat(distance_km=10))
    assert recovery_days(event("court", "badminton", []), cat()) == 2


def test_weeks_label_is_singular_for_one_week():
    assert _weeks(0) == "Under a week"
    assert _weeks(1) == "1 week"
    assert _weeks(9) == "9 weeks"
