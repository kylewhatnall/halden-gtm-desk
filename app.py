"""Halden GTM Desk: a small FastAPI app that runs the intake → brief → bets → queue loop.

Everything here is invented. Halden is a fictional field service software company. The model calls go
through the Anthropic API with a server-side key; the browser never sees it. Without a key the app runs in
offline mode and replays the recorded examples, so the demo and the tests work on a laptop with no account.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
SKILLS = ROOT / "skills"
EXAMPLES = ROOT / "examples"

MODEL = os.environ.get("HALDEN_MODEL", "claude-sonnet-4-5")
DAILY_CAP = int(os.environ.get("HALDEN_DAILY_CAP", "40"))
IP_HOURLY_CAP = int(os.environ.get("HALDEN_IP_HOURLY_CAP", "5"))
OFFLINE = os.environ.get("HALDEN_OFFLINE") == "1" or not os.environ.get("ANTHROPIC_API_KEY")

app = FastAPI(title="Halden GTM Desk", docs_url=None, redoc_url=None)


# ---------------------------------------------------------------- models


class Intake(BaseModel):
    feature: str = Field(min_length=2, max_length=120)
    what: str = Field(min_length=10, max_length=1200)
    asked_by: str = Field(min_length=2, max_length=200)
    launch_window: str = Field(min_length=2, max_length=60)
    pricing_impact: str = Field(pattern="^(none|add-on|tier gate)$")
    example_id: str | None = None


class BetsRequest(BaseModel):
    intake: Intake
    brief: dict


# ---------------------------------------------------------------- skills and prompts


def load_skill(name: str) -> str:
    return (SKILLS / f"{name}.md").read_text()


def system_prompt(step: str) -> str:
    """The model reads the voice file plus the skill for the step. Both are plain markdown in skills/."""
    return load_skill("halden_voice") + "\n\n" + load_skill(step)


def brief_user_message(intake: Intake) -> str:
    return (
        "Feature intake from a Halden product manager.\n\n"
        f"Feature name: {intake.feature}\n"
        f"What it does: {intake.what}\n"
        f"Who asked for it: {intake.asked_by}\n"
        f"Launch window: {intake.launch_window}\n"
        f"Pricing impact: {intake.pricing_impact}\n\n"
        "Write the GTM brief as JSON following the schema in your instructions. JSON only."
    )


def bets_user_message(intake: Intake, brief: dict) -> str:
    return (
        f"Feature: {intake.feature}\nLaunch window: {intake.launch_window}\n"
        f"Pricing impact: {intake.pricing_impact}\n\n"
        "Approved GTM brief:\n" + json.dumps(brief, indent=2) + "\n\n"
        "Propose the marketing bets as JSON following the schema in your instructions. JSON only."
    )


# ---------------------------------------------------------------- rate limits (in memory, enough for a demo)

_day_runs: dict[str, int] = defaultdict(int)
_ip_runs: dict[str, list[float]] = defaultdict(list)


def check_limits(request: Request) -> None:
    today = datetime.now(UTC).date().isoformat()
    if _day_runs[today] >= DAILY_CAP:
        raise HTTPException(
            429, "Demo limit reached for today. It resets at midnight UTC; the code is free to run locally."
        )
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _ip_runs[ip] = [t for t in _ip_runs[ip] if now - t < 3600]
    if len(_ip_runs[ip]) >= IP_HOURLY_CAP:
        raise HTTPException(
            429, f"That's {IP_HOURLY_CAP} runs in an hour from this address. Try again later or run it locally."
        )
    _ip_runs[ip].append(now)
    _day_runs[today] += 1


def usage() -> dict:
    today = datetime.now(UTC).date().isoformat()
    return {"runs_today": _day_runs[today], "daily_cap": DAILY_CAP, "offline": OFFLINE, "model": MODEL}


# ---------------------------------------------------------------- examples


def load_examples() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(EXAMPLES.glob("*.json"))]


def find_example(intake: Intake) -> dict:
    """Offline mode: match the chosen example by id, then by feature name, else replay the first one."""
    exs = load_examples()
    for ex in exs:
        if intake.example_id and ex["id"] == intake.example_id:
            return ex
    for ex in exs:
        if ex["intake"]["feature"].lower() == intake.feature.strip().lower():
            return ex
    return exs[0]


# ---------------------------------------------------------------- streaming


async def replay(text: str) -> AsyncIterator[str]:
    """Offline mode streams the recorded output in small pieces so the UI behaves the same way."""
    import asyncio

    for i in range(0, len(text), 24):
        yield text[i : i + 24]
        await asyncio.sleep(0.01)


async def call_model(system: str, user: str, max_tokens: int) -> AsyncIterator[str]:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic()
    async with client.messages.stream(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    ) as stream:
        async for chunk in stream.text_stream:
            yield chunk


def sse(gen: AsyncIterator[str]) -> StreamingResponse:
    async def body():
        async for piece in gen:
            yield "data: " + json.dumps(piece) + "\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(body(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------- routes


@app.get("/")
def index():
    return FileResponse(ROOT / "index.html")


@app.get("/api/examples")
def examples():
    return [{k: ex[k] for k in ("id", "intake")} for ex in load_examples()]


@app.get("/api/usage")
def get_usage():
    return usage()


@app.get("/api/under-the-hood")
def under_the_hood():
    return {
        "model": MODEL,
        "skills": {name: load_skill(name) for name in ("halden_voice", "brief", "bets")},
        "brief_system": system_prompt("brief"),
        "bets_system": system_prompt("bets"),
        "offline": OFFLINE,
    }


@app.post("/api/brief")
async def brief(intake: Intake, request: Request):
    if OFFLINE:
        ex = find_example(intake)
        return sse(replay(json.dumps(ex["brief"], indent=2)))
    check_limits(request)
    return sse(call_model(system_prompt("brief"), brief_user_message(intake), 2000))


@app.post("/api/bets")
async def bets(req: BetsRequest, request: Request):
    if OFFLINE:
        ex = find_example(req.intake)
        return sse(replay(json.dumps(ex["bets"], indent=2)))
    check_limits(request)
    return sse(call_model(system_prompt("bets"), bets_user_message(req.intake, req.brief), 2500))


@app.get("/healthz")
def healthz():
    return {"ok": True, **usage()}
