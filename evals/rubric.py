"""Rubric for a Halden run. Every check is deterministic, so a prompt change gets the same grade twice.

score_brief and score_bets return (points, max_points, findings). A finding is a short string naming what
failed. The checks encode the house rules in skills/*.md; when a rule changes there, change it here too.
"""

from __future__ import annotations

import re

HYPE = [
    "seamless",
    "robust",
    "leverage",
    "empower",
    "cutting edge",
    "cutting-edge",
    "game changer",
    "game-changer",
    "transformative",
    "unlock",
    "supercharge",
    "elevate",
    "revolutioniz",
    "next level",
    "best in class",
    "world class",
    "world-class",
    "delight",
    "frictionless",
    "effortless",
]
SIGNPOSTS = ["here's the thing", "the bottom line", "let's be clear", "at the end of the day"]
ALLOWED_CHANNELS = [
    "in-app",
    "release notes",
    "customer email",
    "email",
    "csm",
    "battlecard",
    "help center",
    "help article",
    "webinar",
    "partner",
    "trade association",
    "direct mail",
    "sales",
]
TIERS = {"major", "standard", "quiet"}


def _text(obj) -> str:
    import json

    return json.dumps(obj).lower()


def _prose_findings(obj, label: str) -> list[str]:
    t = _text(obj)
    out = []
    for w in HYPE:
        if w in t:
            out.append(f"{label}: hype word '{w}'")
    for s in SIGNPOSTS:
        if s in t:
            out.append(f"{label}: signpost '{s}'")
    if "—" in t or " -- " in t:
        out.append(f"{label}: em dash")
    return out


def score_brief(brief: dict, expect: dict | None = None) -> tuple[int, int, list[str]]:
    expect = expect or {}
    f: list[str] = []
    pts, maxp = 0, 0

    def check(ok: bool, weight: int, msg: str):
        nonlocal pts, maxp
        maxp += weight
        if ok:
            pts += weight
        else:
            f.append(msg)

    required = ["launch_tier", "tier_reason", "positioning", "segments", "channels", "risks", "sales_proof"]
    check(
        all(k in brief for k in required), 10, "brief: missing keys " + ", ".join(k for k in required if k not in brief)
    )
    tier = str(brief.get("launch_tier", "")).lower()
    check(tier in TIERS, 5, f"brief: tier '{tier}' not one of major, standard, quiet")
    if expect.get("tier"):
        check(tier in expect["tier"], 10, f"brief: tier '{tier}', expected one of {expect['tier']}")
    check(
        len(str(brief.get("tier_reason", "")).split()) >= 8, 3, "brief: tier reason is too short to defend the choice"
    )

    pos = str(brief.get("positioning", ""))
    words = len(pos.split())
    check(8 <= words <= 40, 5, f"brief: positioning is {words} words; a dispatcher should be able to repeat it")
    check(pos.count(".") <= 2, 2, "brief: positioning is more than one sentence")

    segs = brief.get("segments") or []
    check(len(segs) == 3, 8, f"brief: {len(segs)} segments, rule says exactly three")
    check(
        all(all(k in s and str(s[k]).strip() for k in ("name", "who", "message", "proof_needed")) for s in segs),
        5,
        "brief: a segment is missing name, who, message or proof_needed",
    )
    ch = brief.get("channels") or []
    lo, hi = (2, expect.get("max_channels", 6)) if tier == "quiet" else (4, expect.get("max_channels", 6))
    check(lo <= len(ch) <= hi, 6, f"brief: {len(ch)} channels, expected {lo} to {hi} for a {tier or 'unknown'} release")
    check(
        all(any(a in str(c.get("channel", "")).lower() for a in ALLOWED_CHANNELS) for c in ch),
        4,
        "brief: a channel is not one Halden has",
    )
    check(all(str(c.get("timing", "")).strip() for c in ch), 3, "brief: a channel has no timing")

    risks = brief.get("risks") or []
    check(2 <= len(risks) <= 4, 4, f"brief: {len(risks)} risks, expected two to four")
    check(all(str(r.get("signal", "")).strip() for r in risks), 4, "brief: a risk has no signal")
    if expect.get("pricing_risk"):
        rt = _text(risks)
        check(
            any(w in rt for w in ("pric", "tier", "upgrade", "paywall", "add-on", "cost")),
            6,
            "brief: pricing impact set but no risk mentions price, tier or upgrade",
        )

    sp = brief.get("sales_proof") or []
    check(3 <= len(sp) <= 5, 3, f"brief: {len(sp)} sales proof items, expected three to five")

    for m in expect.get("mentions", []):
        check(m.lower() in _text(brief), 2, f"brief: never mentions '{m}'")

    pf = _prose_findings(brief, "brief")
    check(not pf, 10, "; ".join(pf) if pf else "")
    return pts, maxp, [x for x in f if x]


def score_bets(bets: dict, brief: dict | None = None) -> tuple[int, int, list[str]]:
    f: list[str] = []
    pts, maxp = 0, 0

    def check(ok: bool, weight: int, msg: str):
        nonlocal pts, maxp
        maxp += weight
        if ok:
            pts += weight
        else:
            f.append(msg)

    items = bets.get("bets") or []
    check(4 <= len(items) <= 6, 8, f"bets: {len(items)} bets, expected four to six")
    keys = ("title", "hypothesis", "change", "win_target", "window_weeks", "impact", "effort", "owner_role")
    check(all(all(k in b for k in keys) for b in items), 8, "bets: a bet is missing a field")
    check(
        all(
            str(b.get("hypothesis", "")).lower().startswith("if ")
            and " then " in str(b.get("hypothesis", "")).lower()
            and " because " in str(b.get("hypothesis", "")).lower()
            for b in items
        ),
        8,
        "bets: a hypothesis is not in the form If ..., then ..., because ...",
    )
    check(all(re.search(r"\d", str(b.get("win_target", ""))) for b in items), 8, "bets: a win target has no number")
    check(
        all(
            any(
                w in str(b.get("win_target", "")).lower()
                for w in ("against", "assum", "baseline", "from", "versus", "vs", "last")
            )
            for b in items
        ),
        4,
        "bets: a win target names no baseline or assumption",
    )
    check(
        all(isinstance(b.get("window_weeks"), int) and 2 <= b["window_weeks"] <= 6 for b in items),
        5,
        "bets: a window is outside two to six weeks",
    )
    check(
        all(
            isinstance(b.get("impact"), int)
            and 1 <= b["impact"] <= 5
            and isinstance(b.get("effort"), int)
            and 1 <= b["effort"] <= 5
            for b in items
        ),
        4,
        "bets: a score is outside 1 to 5",
    )
    check(any(b.get("effort", 9) <= 2 and b.get("window_weeks", 9) <= 2 for b in items), 5, "bets: no cheap, fast bet")
    check(not all(b.get("impact") == 5 for b in items), 3, "bets: every bet scored impact 5, which is not honest")
    check(
        all(" and " not in str(b.get("change", "")).lower() for b in items),
        3,
        "bets: a change contains 'and', which is usually two bets",
    )
    titles = [str(b.get("title", "")).lower() for b in items]
    check(len(set(titles)) == len(titles), 2, "bets: duplicate titles")
    if brief:
        plays = [str(c.get("play", "")).lower() for c in (brief.get("channels") or [])]
        check(
            not any(str(b.get("change", "")).lower() in plays for b in items),
            3,
            "bets: a change repeats a channel play from the brief word for word",
        )
    pf = _prose_findings(bets, "bets")
    check(not pf, 8, "; ".join(pf) if pf else "")
    return pts, maxp, [x for x in f if x]
