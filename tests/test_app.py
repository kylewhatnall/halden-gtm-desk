"""Offline tests. They replay the recorded examples and never touch the network.
Run `pytest --live` with ANTHROPIC_API_KEY set to add one real call per step."""

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("HALDEN_OFFLINE", "1")

from fastapi.testclient import TestClient

import app as halden

ROOT = Path(halden.__file__).parent
client = TestClient(halden.app)

BRIEF_KEYS = {"launch_tier", "tier_reason", "positioning", "segments", "channels", "risks", "sales_proof"}
BET_KEYS = {"title", "hypothesis", "change", "win_target", "window_weeks", "impact", "effort", "owner_role"}
BANNED = [
    "seamless",
    "robust",
    "leverage",
    "empower",
    "cutting edge",
    "game changer",
    "transformative",
    "unlock",
    "supercharge",
]


def examples():
    return [json.loads(p.read_text()) for p in sorted((ROOT / "examples").glob("*.json"))]


def check_brief(b):
    assert BRIEF_KEYS <= set(b)
    assert b["launch_tier"] in {"major", "standard", "quiet"}
    assert len(b["segments"]) == 3
    assert 4 <= len(b["channels"]) <= 6
    assert 2 <= len(b["risks"]) <= 4
    assert 3 <= len(b["sales_proof"]) <= 5
    text = json.dumps(b).lower()
    for w in BANNED:
        assert w not in text, w
    assert "—" not in text


def check_bets(b):
    bets = b["bets"]
    assert 4 <= len(bets) <= 6
    for x in bets:
        assert BET_KEYS <= set(x)
        assert 1 <= x["impact"] <= 5 and 1 <= x["effort"] <= 5
        assert 2 <= x["window_weeks"] <= 6
        assert x["hypothesis"].startswith("If ")
    assert any(x["effort"] <= 2 and x["window_weeks"] <= 2 for x in bets), "needs one cheap, fast bet"
    text = json.dumps(b).lower()
    for w in BANNED:
        assert w not in text, w


def test_examples_are_well_formed():
    ex = examples()
    assert len(ex) == 3
    for e in ex:
        assert {"id", "intake", "brief", "bets"} <= set(e)
        halden.Intake(**e["intake"])
        check_brief(e["brief"])
        check_bets(e["bets"])


def test_skills_load_and_prompt_assembles():
    for name in ("halden_voice", "brief", "bets"):
        assert len(halden.load_skill(name)) > 200
    assert "JSON only" in halden.system_prompt("brief")
    assert "Output schema" in halden.system_prompt("bets")


def test_index_and_examples_routes():
    assert client.get("/").status_code == 200
    ex = client.get("/api/examples").json()
    assert [e["id"] for e in ex] == ["callback-tracker", "parts-on-truck", "after-hours-routing"]
    hood = client.get("/api/under-the-hood").json()
    assert set(hood["skills"]) == {"halden_voice", "brief", "bets"}
    assert client.get("/healthz").json()["ok"] is True


def read_sse(resp):
    text = ""
    for line in resp.text.splitlines():
        if line.startswith("data: ") and line != "data: {}":
            text += json.loads(line[6:])
    return text


def test_offline_brief_and_bets_replay_the_example():
    ex = examples()[1]
    r = client.post("/api/brief", json=ex["intake"])
    assert r.status_code == 200
    brief = json.loads(read_sse(r))
    assert brief == ex["brief"]
    r = client.post("/api/bets", json={"intake": ex["intake"], "brief": brief})
    assert json.loads(read_sse(r)) == ex["bets"]


def test_intake_validation():
    r = client.post(
        "/api/brief",
        json={"feature": "x", "what": "short", "asked_by": "a", "launch_window": "b", "pricing_impact": "free"},
    )
    assert r.status_code == 422


def test_rate_limits(monkeypatch):
    from fastapi import HTTPException

    class Req:
        class client:
            host = "203.0.113.9"

    monkeypatch.setattr(halden, "DAILY_CAP", 3)
    monkeypatch.setattr(halden, "IP_HOURLY_CAP", 2)
    halden._day_runs.clear()
    halden._ip_runs.clear()
    halden.check_limits(Req())
    halden.check_limits(Req())
    with pytest.raises(HTTPException) as e:
        halden.check_limits(Req())
    assert e.value.status_code == 429 and "hour" in e.value.detail
    Req.client.host = "203.0.113.10"
    halden.check_limits(Req())
    with pytest.raises(HTTPException) as e:
        halden.check_limits(Req())
    assert "Demo limit" in e.value.detail


@pytest.mark.skipif(not os.environ.get("ANTHROPIC_API_KEY"), reason="no key")
def test_live_round_trip(live):
    if not live:
        pytest.skip("pass --live")
    import asyncio

    ex = examples()[0]
    intake = halden.Intake(**ex["intake"])

    async def run(system, user, n):
        return "".join([c async for c in halden.call_model(system, user, n)])

    text = asyncio.run(run(halden.system_prompt("brief"), halden.brief_user_message(intake), 2000))
    brief = json.loads(text[text.index("{") : text.rindex("}") + 1])
    check_brief(brief)
    text = asyncio.run(run(halden.system_prompt("bets"), halden.bets_user_message(intake, brief), 2500))
    check_bets(json.loads(text[text.index("{") : text.rindex("}") + 1]))
