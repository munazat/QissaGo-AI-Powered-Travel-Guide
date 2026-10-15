"""API tests: auth, chat, generate, save, list (against the test PostgreSQL database)."""

import datetime as dt

API = "/api/v1"
FUTURE = (dt.date.today() + dt.timedelta(days=20)).isoformat()


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_register_login_me(client):
    r = client.post(
        f"{API}/auth/register", json={"name": "Ali Raza", "email": "Ali@Example.com", "password": "pass1234"}
    )
    assert r.status_code == 201
    assert (
        client.post(
            f"{API}/auth/register", json={"name": "Ali", "email": "ali@example.com", "password": "pass1234"}
        ).status_code
        == 409
    )
    assert client.post(f"{API}/auth/login", json={"email": "ali@example.com", "password": "nope"}).status_code == 401
    token = client.post(f"{API}/auth/login", json={"email": "ali@example.com", "password": "pass1234"}).json()["token"]
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["name"] == "Ali Raza" and me["email"] == "ali@example.com"


def test_requires_login(client):
    assert client.post(f"{API}/chat/sessions").status_code == 401
    assert client.get(f"{API}/itineraries", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_meta(client):
    data = client.get(f"{API}/meta").json()
    assert {c["id"] for c in data["cities"]} == {
        "lahore",
        "islamabad",
        "karachi",
        "multan",
        "peshawar",
        "murree",
        "hunza",
        "skardu",
        "swat",
        "kalam",
        "bahawalpur",
    }
    assert len(data["interests"]) == 8


def test_chat_to_saved_plan(client, auth):
    s = client.post(f"{API}/chat/sessions", headers=auth).json()
    sid = s["session_id"]
    assert s["awaiting"] == "city"
    t = client.post(
        f"{API}/chat/sessions/{sid}/messages",
        headers=auth,
        json={"text": f"3 days in Lahore from {FUTURE}, family of 4, 90k, history"},
    ).json()
    assert t["ready"] and t["awaiting"] == "confirm"
    t = client.post(f"{API}/chat/sessions/{sid}/messages", headers=auth, json={"text": "Create plans"}).json()
    assert t["action"] == "generate"

    history = client.get(f"{API}/chat/sessions/{sid}", headers=auth).json()
    assert [m["role"] for m in history["messages"]] == ["bot", "user", "bot", "user", "bot"]

    gen = client.post(f"{API}/itineraries/generate", headers=auth, json={"session_id": sid})
    assert gen.status_code == 200, gen.text
    plans = gen.json()["itineraries"]
    assert len(plans) == 3 and len(gen.json()["trace"]) == 8

    first = plans[0]["id"]
    assert client.get(f"{API}/itineraries", headers=auth).json() == []
    assert client.post(f"{API}/itineraries/{first}/save", headers=auth).json()["saved"] is True
    saved = client.get(f"{API}/itineraries", headers=auth).json()
    assert [p["id"] for p in saved] == [first]
    again = client.get(f"{API}/itineraries/batch/{plans[0]['batch_id']}", headers=auth).json()
    assert len(again) == 3
    client.delete(f"{API}/itineraries/{first}/save", headers=auth)
    assert client.get(f"{API}/itineraries", headers=auth).json() == []


def test_recent_shows_best_option_per_batch(client, auth):
    assert client.get(f"{API}/itineraries/recent", headers=auth).json() == []
    prefs = {
        "city": "lahore",
        "start_date": FUTURE,
        "days": 2,
        "budget": 80000,
        "group_size": 2,
        "group_type": "couple",
    }
    batches = []
    for _ in range(2):
        gen = client.post(f"{API}/itineraries/generate", headers=auth, json={"preferences": prefs})
        assert gen.status_code == 200, gen.text
        batches.append(gen.json()["itineraries"])
    recent = client.get(f"{API}/itineraries/recent", headers=auth).json()
    assert len(recent) == 2
    assert {r["batch_id"] for r in recent} == {b[0]["batch_id"] for b in batches}
    for r in recent:
        options = next(b for b in batches if b[0]["batch_id"] == r["batch_id"])
        assert r["match_score"] == max(o["match_score"] for o in options)
    assert client.get(f"{API}/itineraries/recent").status_code == 401


def test_button_patch(client, auth):
    sid = client.post(f"{API}/chat/sessions", headers=auth).json()["session_id"]
    t = client.post(
        f"{API}/chat/sessions/{sid}/messages",
        headers=auth,
        json={"patch": {"city": "karachi", "days": 2, "group_type": "couple"}},
    ).json()
    assert t["preferences"]["city"] == "karachi" and t["awaiting"] == "start_date"


def test_generate_from_quick_form(client, auth):
    prefs = {
        "city": "islamabad",
        "start_date": FUTURE,
        "days": 2,
        "budget": 60000,
        "group_type": "friends",
        "group_size": 3,
        "interests": ["nature"],
        "pace": "relaxed",
    }
    r = client.post(f"{API}/itineraries/generate", headers=auth, json={"preferences": prefs})
    assert r.status_code == 200
    plan = r.json()["itineraries"][0]
    assert plan["city_name"] == "Islamabad" and plan["days"] == 2


def test_generate_rejects_incomplete(client, auth):
    r = client.post(f"{API}/itineraries/generate", headers=auth, json={"preferences": {"city": "lahore"}})
    assert r.status_code == 400 and "Missing" in r.json()["detail"]


def test_cannot_see_other_users_plans(client, auth):
    prefs = {"city": "lahore", "start_date": FUTURE, "days": 1, "budget": 30000, "group_type": "solo"}
    plan_id = client.post(f"{API}/itineraries/generate", headers=auth, json={"preferences": prefs}).json()[
        "itineraries"
    ][0]["id"]
    other = client.post(
        f"{API}/auth/register", json={"name": "Other", "email": "other@example.com", "password": "secret123"}
    ).json()
    r = client.get(f"{API}/itineraries/{plan_id}", headers={"Authorization": f"Bearer {other['token']}"})
    assert r.status_code == 404
