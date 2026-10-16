from tests.conftest import registration_body


def _event(client, **params):
    return client.get("/api/events", params=params).json()["items"]


def _tmm(client):
    slug = _event(client, q="tata mumbai marathon")[0]["slug"]
    return client.get(f"/api/events/{slug}").json()


def test_register_gets_a_bib_and_appears_in_season(client, runner):
    ev = _tmm(client)
    half = next(c for c in ev["categories"] if c["name"] == "Half Marathon")
    resp = client.post("/api/registrations", json=registration_body(runner["id"], ev["slug"], half["id"]))
    assert resp.status_code == 201, resp.text
    reg = resp.json()
    assert reg["bib_number"] >= 1001
    assert reg["code"].startswith("SL")
    season = client.get(f"/api/athletes/{runner['id']}/season").json()
    assert season["timeline"][0]["registration"]["code"] == reg["code"]
    assert client.get(f"/api/registrations/{reg['code']}").json()["status"] == "confirmed"


def test_duplicate_registration_is_refused(client, runner):
    ev = _tmm(client)
    tenk = next(c for c in ev["categories"] if c["name"] == "Open 10K")
    body = registration_body(runner["id"], ev["slug"], tenk["id"])
    assert client.post("/api/registrations", json=body).status_code == 201
    second = client.post("/api/registrations", json=body)
    assert second.status_code == 409
    assert "already registered" in second.json()["detail"]


def test_minimum_age_is_enforced_on_race_day(client, runner):
    ev = _tmm(client)
    full = next(c for c in ev["categories"] if c["name"] == "Marathon")
    body = registration_body(runner["id"], ev["slug"], full["id"], date_of_birth="2012-01-01")
    resp = client.post("/api/registrations", json=body)
    assert resp.status_code == 422
    assert "18" in resp.json()["detail"]


def test_bad_phone_and_missing_declaration_are_rejected(client, runner):
    ev = _tmm(client)
    cat = ev["categories"][0]["id"]
    assert (
        client.post(
            "/api/registrations", json=registration_body(runner["id"], ev["slug"], cat, phone="12345")
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/registrations", json=registration_body(runner["id"], ev["slug"], cat, medical_declaration=False)
        ).status_code
        == 422
    )
    same = registration_body(runner["id"], ev["slug"], cat, emergency_phone="9876543210")
    assert client.post("/api/registrations", json=same).status_code == 422


def test_closed_events_refuse_entries(client, runner):
    closed = _event(client, sport="tennis") + _event(client, sport="running")
    ev = next((e for e in closed if e["registration_status"] == "closed"), None)
    if ev is None:
        return
    body = registration_body(runner["id"], ev["slug"], ev["categories"][0]["id"])
    resp = client.post("/api/registrations", json=body)
    assert resp.status_code == 409


def test_doubles_need_a_partner(client, runner):
    for ev in _event(client, sport="badminton") + _event(client, sport="pickleball"):
        if ev["registration_status"] == "closed":
            continue
        cat = next((c for c in ev["categories"] if "doubles" in c["name"].lower() and "35" not in c["name"]), None)
        if cat is None:
            continue
        resp = client.post("/api/registrations", json=registration_body(runner["id"], ev["slug"], cat["id"]))
        if resp.status_code == 422 and "partner" in resp.json()["detail"]:
            ok = client.post(
                "/api/registrations",
                json=registration_body(runner["id"], ev["slug"], cat["id"], partner_name="Doubles Partner"),
            )
            assert ok.status_code in (201, 422)  # 422 only if an age rule applies to this draw
            return
    raise AssertionError("no doubles draw found to test")


def test_cancel_frees_the_category(client, runner):
    ev = _tmm(client)
    dream = next(c for c in ev["categories"] if c["name"] == "Dream Run")
    body = registration_body(runner["id"], ev["slug"], dream["id"])
    code = client.post("/api/registrations", json=body).json()["code"]
    assert client.delete(f"/api/registrations/{code}", params={"athlete_id": "someone-else"}).status_code == 404
    assert client.delete(f"/api/registrations/{code}", params={"athlete_id": runner["id"]}).json()["status"] == (
        "cancelled"
    )
    assert client.post("/api/registrations", json=body).status_code == 201


def test_saved_events_and_recovery_warning(client, runner):
    ev = _tmm(client)
    half = next(c for c in ev["categories"] if c["name"] == "Half Marathon")
    client.post("/api/registrations", json=registration_body(runner["id"], ev["slug"], half["id"]))
    week_later = next(
        e for e in _event(client, sport="running", month="2027-01") if "2027-01-18" <= e["start_date"] <= "2027-01-24"
    )
    assert client.post(f"/api/athletes/{runner['id']}/saved", json={"event": week_later["slug"]}).status_code == 201
    season = client.get(f"/api/athletes/{runner['id']}/season").json()
    assert any(w["level"] == "tight" for w in season["warnings"])
    assert client.delete(f"/api/athletes/{runner['id']}/saved/{week_later['slug']}").json()["saved"] is False
