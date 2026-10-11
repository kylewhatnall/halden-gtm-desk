#!/usr/bin/env python3
"""Run the Halden evals and write a scorecard.

    python3 evals/run.py                # offline: grade the recorded examples with the rubric (no key needed)
    python3 evals/run.py --live         # call the model for every case in evals/cases.json, then grade
    python3 evals/run.py --live -n 2    # two runs per case, to see variance

Writes evals/results/<date>.md and prints the summary. Exit code 1 when the average falls under PASS.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evals"))

from rubric import score_bets, score_brief  # noqa: E402

import app as halden  # noqa: E402

PASS = 85


def examples():
    return {e["id"]: e for e in (json.loads(p.read_text()) for p in sorted((ROOT / "examples").glob("*.json")))}


def parse(text: str) -> dict:
    return json.loads(text[text.index("{") : text.rindex("}") + 1])


async def live_run(intake: halden.Intake) -> tuple[dict, dict]:
    async def collect(system, user, n):
        return "".join([c async for c in halden.call_model(system, user, n)])

    brief = parse(await collect(halden.system_prompt("brief"), halden.brief_user_message(intake), 2000))
    bets = parse(await collect(halden.system_prompt("bets"), halden.bets_user_message(intake, brief), 2500))
    return brief, bets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("-n", type=int, default=1)
    args = ap.parse_args()
    if args.live and not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("--live needs ANTHROPIC_API_KEY")

    cases = json.loads((ROOT / "evals" / "cases.json").read_text())
    ex = examples()
    rows = []
    for case in cases:
        intake = halden.Intake(**(ex[case["id"]]["intake"] if case.get("from_example") else case["intake"]))
        for i in range(args.n if args.live else 1):
            if args.live:
                brief, bets = asyncio.run(live_run(intake))
            elif case.get("from_example"):
                brief, bets = ex[case["id"]]["brief"], ex[case["id"]]["bets"]
            else:
                continue  # offline mode has no recorded output for the extra cases
            bp, bm, bf = score_brief(brief, case.get("expect"))
            pp, pm, pf = score_bets(bets, brief)
            total = round(100 * (bp + pp) / (bm + pm))
            rows.append(
                {
                    "case": case["id"],
                    "run": i + 1,
                    "score": total,
                    "brief": f"{bp}/{bm}",
                    "bets": f"{pp}/{pm}",
                    "tier": brief.get("launch_tier"),
                    "findings": bf + pf,
                }
            )

    avg = round(sum(r["score"] for r in rows) / max(len(rows), 1))
    mode = f"live ({halden.MODEL})" if args.live else "offline (recorded examples)"
    today = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    out = [
        f"# Halden eval scorecard, {today}",
        "",
        f"Mode: {mode}. Average {avg}/100, pass mark {PASS}.",
        "",
        "| Case | Run | Score | Brief | Bets | Tier | Findings |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        out.append(
            f"| {r['case']} | {r['run']} | {r['score']} | {r['brief']} | {r['bets']} | {r['tier']} | "
            + ("; ".join(r["findings"]) or "none")
            + " |"
        )
    text = "\n".join(out) + "\n"
    results = ROOT / "evals" / "results"
    results.mkdir(exist_ok=True)
    path = results / (datetime.now(UTC).strftime("%Y-%m-%d_%H%M") + ("_live" if args.live else "_offline") + ".md")
    path.write_text(text)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        Path(summary).write_text(text)
    sys.exit(0 if avg >= PASS else 1)


if __name__ == "__main__":
    main()
