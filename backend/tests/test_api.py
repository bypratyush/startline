"""End-to-end API behaviour: probes, catalogue, profiles, discovery, detail pages."""

from tests.conftest import RUNNER, SWIMMER


def test_health_is_cheap_and_ready_checks_the_catalogue(client):
    assert client.get("/health").json() == {"status": "ok"}
    ready = client.get("/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ready"
    assert body["sports"] == 13
    assert body["events"] >= 200


def test_root_points_at_docs(client):
    body = client.get("/").json()
    assert body["name"] == "StartLine"
    assert body["docs"] == "/docs"


def test_metrics_exposes_http_and_business_metrics(client):
    client.get("/api/events")
    text = client.get("/metrics").text
    assert "startline_http_requests_total" in text
    assert "startline_event_searches_total" in text


def test_every_sport_asks_two_or_three_required_questions(client):
    sports = client.get("/api/sports").json()
    assert len(sports) == 13
    for s in sports:
        assert 2 <= len(s["questions"]) <= 3, s["slug"]
        for q in s["questions"]:
            assert q["prompt"]
            assert len(q["options"]) >= 2
        assert s["events"] > 0, f"{s['slug']} has no upcoming events"


def test_cities_are_tier_1_and_2_only(client):
    cities = client.get("/api/cities").json()
    assert {c["tier"] for c in cities} == {1, 2}
    assert sum(1 for c in cities if c["tier"] == 1) == 8
    assert all(-90 <= c["lat"] <= 90 for c in cities)


def test_unknown_sport_is_404(client):
    assert client.get("/api/sports/curling").status_code == 404


def test_profile_derives_level_from_answers(swimmer):
    levels = {s["sport"]["slug"]: s["level"] for s in swimmer["sports"]}
    assert levels == {"swimming": "beginner", "triathlon": "beginner"}
    labels = swimmer["sports"][0]["labels"]
    assert labels and all(lbl["answer"] for lbl in labels)


def test_profile_requires_every_question(client):
    body = {**SWIMMER, "sports": [{"sport": "swimming", "answers": {"level": "beginner"}}]}
    resp = client.post("/api/athletes", json=body)
    assert resp.status_code == 422
    assert "please answer" in resp.json()["detail"]


def test_profile_rejects_unknown_answers_and_duplicate_sports(client):
    bad = {
        **RUNNER,
        "sports": [
            {"sport": "running", "answers": {"level": "pro", "run_longest_recent": "lt5", "run_5k_band": "none"}}
        ],
    }
    assert client.post("/api/athletes", json=bad).status_code == 422
    dup = {**RUNNER, "sports": RUNNER["sports"] * 2}
    assert client.post("/api/athletes", json=dup).status_code == 422
    unknown_city = {**RUNNER, "city": "atlantis"}
    assert client.post("/api/athletes", json=unknown_city).status_code == 404


def test_patch_turns_recommendations_off(client, runner):
    resp = client.patch(f"/api/athletes/{runner['id']}", json={"recommendations_enabled": False})
    assert resp.json()["recommendations_enabled"] is False


def test_put_replaces_sports(client, runner):
    body = {**SWIMMER, "name": "Switched Sports"}
    resp = client.put(f"/api/athletes/{runner['id']}", json=body)
    assert resp.status_code == 200
    assert {s["sport"]["slug"] for s in resp.json()["sports"]} == {"swimming", "triathlon"}


def test_discovery_puts_recommended_events_first(client, swimmer):
    data = client.get("/api/events", params={"athlete_id": swimmer["id"], "sport": "swimming,triathlon"}).json()
    assert data["recommendations"] == "on"
    assert data["recommended_count"] > 0
    items = data["items"]
    first = items[0]
    assert first["recommended"] is True
    assert first["sport"]["slug"] in ("swimming", "triathlon")
    assert first["match"]["reasons"]
    # every recommended item comes before every non-recommended one, best score first
    flags = [i["recommended"] for i in items]
    assert flags == sorted(flags, reverse=True)
    scores = [i["match"]["score"] for i in items if i["recommended"]]
    assert scores == sorted(scores, reverse=True)


def test_beginner_swimmer_is_not_pushed_to_long_swims(client, swimmer):
    items = client.get("/api/events", params={"athlete_id": swimmer["id"], "sport": "swimming"}).json()["items"]
    for item in items:
        if item["recommended"]:
            cat = next(c for c in item["categories"] if c["id"] == item["match"]["category_id"])
            assert cat["distance_km"] is None or cat["distance_km"] <= 2.5, (item["name"], cat)


def test_recommendations_can_be_switched_off(client, swimmer):
    client.patch(f"/api/athletes/{swimmer['id']}", json={"recommendations_enabled": False})
    data = client.get("/api/events", params={"athlete_id": swimmer["id"], "sport": "swimming"}).json()
    assert data["recommendations"] == "off"
    assert all(i["match"] is None for i in data["items"])
    dates = [i["start_date"] for i in data["items"]]
    assert dates == sorted(dates)


def test_filters_by_sport_city_radius_and_month(client):
    data = client.get("/api/events", params={"sport": "running", "city": "pune", "radius_km": 60}).json()
    assert data["total"] > 0
    assert all(i["sport"]["slug"] == "running" and i["distance_km"] <= 60 for i in data["items"])
    month = client.get("/api/events", params={"month": "2027-01"}).json()
    assert all(i["start_date"].startswith("2027-01") for i in month["items"])
    assert "running" in month["facets"]["sports"]


def test_search_matches_name_and_city(client):
    data = client.get("/api/events", params={"q": "mumbai marathon"}).json()
    assert any("Mumbai Marathon" in i["name"] for i in data["items"])


def test_event_detail_has_categories_weather_and_match(client, runner):
    slug = client.get("/api/events", params={"q": "tata mumbai marathon"}).json()["items"][0]["slug"]
    d = client.get(f"/api/events/{slug}", params={"athlete_id": runner["id"]}).json()
    assert d["categories"] and d["sources"]
    assert d["weather"]["month"] == "January"
    assert d["match"]["category_name"]
    assert d["distance_km"] is not None
    assert client.get("/api/events/nope-2027").status_code == 404


def test_guide_anchors_timeline_to_the_start(client):
    slug = client.get("/api/events", params={"q": "tata mumbai marathon"}).json()["items"][0]["slug"]
    g = client.get(f"/api/events/{slug}/guide").json()
    start = next(t for t in g["timeline"] if t["offset"] == "Start")
    assert start["clock"] == g["category"]["start_time"]
    assert g["kit"] and g["safety"] and g["glossary"]
    assert g["venue"]["maps_url"].startswith("https://www.google.com/maps")


def test_calendar_export(client):
    slug = client.get("/api/events", params={"q": "tata mumbai marathon"}).json()["items"][0]["slug"]
    resp = client.get(f"/api/events/{slug}/calendar.ics")
    assert resp.headers["content-type"].startswith("text/calendar")
    assert "BEGIN:VEVENT" in resp.text and "DTSTART" in resp.text


def test_readiness_form_is_prefilled_from_profile(client, swimmer):
    slug = client.get("/api/events", params={"sport": "swimming"}).json()["items"][0]["slug"]
    form = client.get(f"/api/events/{slug}/readiness-form", params={"athlete_id": swimmer["id"]}).json()
    assert form["has_profile"] is True
    assert form["defaults"]["longest_swim_m"] == 800
    assert form["defaults"]["open_water_swims"] == 2


def test_stats(client):
    s = client.get("/api/stats").json()
    assert s["events_upcoming"] >= 200
    assert s["cities_with_events"] >= 20
    assert len(s["by_sport"]) == 13


def test_saturated_db_pool_returns_503_not_500(client):
    from sqlalchemy.exc import TimeoutError as PoolTimeout

    from app.db import get_db
    from app.main import app

    def exhausted():
        raise PoolTimeout("QueuePool limit reached")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = exhausted
    try:
        resp = client.get("/api/stats")
    finally:
        app.dependency_overrides.clear()
    assert resp.status_code == 503
    assert resp.headers["retry-after"] == "1"
