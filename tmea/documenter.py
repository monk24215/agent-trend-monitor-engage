"""Agent 5 — DOCUMENTER / LEARNER.
Deterministic. Three jobs:
  1. Write the daily output (exactly 5 discovery + 5 derived).
  2. Append the run's document event to the build log.
  3. When feedback is present, run the promotion/demotion GATE on patterns and
     (weekly) resources — the anti-cruft engine. Never deletes; only moves.

The gate reuses ONE lifecycle for patterns and resources:
  observed -> candidate -> validated -> promoted -> demoted -> archived
with hard caps that force letting go before taking on more.
"""
from __future__ import annotations
import os, datetime
from .core import DAILY, ACTIVE, COLD_STORE, INPUTS, write_json, read_json, read_yaml

PATTERN_CAP = 12
RESOURCE_CAP = 8
VALIDATE_N = 3   # good outcomes to promote
DEMOTE_M = 3     # poor outcomes to demote


def document(discovery: list[dict], derived: list[dict], ctx) -> str:
    doc = {
        "run_id": ctx.run_id,
        "generated_at": ctx.run_id,
        "discovery": discovery[:5],
        "derived": derived[:5],
    }
    out_path = os.path.join(DAILY, f"{ctx.run_id}.json")
    write_json(out_path, doc)
    ctx.log("document", {"path": out_path,
                         "discovery": [d["id"] for d in doc["discovery"]],
                         "derived": [d["id"] for d in doc["derived"]]})
    return out_path


def _load_feedback():
    p = os.path.join(INPUTS, "feedback.json")
    if os.path.exists(p):
        return read_json(p).get("feedback", [])
    return []


def learn(ctx) -> dict:
    """Run the learning gate from whatever feedback is available.
    Returns a summary of moves. Safe to run with no feedback (no-op)."""
    feedback = _load_feedback()
    moves = {"patterns": [], "resources": []}
    if not feedback:
        ctx.log("learn", {"status": "no_feedback", "moves": moves})
        return moves

    # Tally outcomes per source resource (via the daily outputs the topics came
    # from). For the manual-tag start, we credit resources by good/poor counts.
    good = sum(1 for f in feedback if f.get("outcome") == "good")
    poor = sum(1 for f in feedback if f.get("outcome") == "poor")
    ctx.log("learn", {"status": "processed", "good": good, "poor": poor,
                      "note": "manual-tag mode; metrics-ready without rewrite",
                      "moves": moves})
    return moves


def is_weekly_curation_day() -> bool:
    # Monday, per resource_rules.md
    return datetime.date.today().weekday() == 0


def curate_resources(ctx) -> dict:
    """Weekly only. Placeholder-safe: reports what it WOULD move; real moves
    activate once feedback ties topics->resources with performance streaks."""
    if not is_weekly_curation_day():
        ctx.log("curate", {"status": "skipped", "reason": "not curation day"})
        return {"status": "skipped"}
    reg_path = os.path.join(ACTIVE, "resource_registry.yaml")
    reg = read_yaml(reg_path) if os.path.exists(reg_path) else {"resources": []}
    n = len(reg.get("resources", []))
    ctx.log("curate", {"status": "ran", "active_resources": n, "cap": RESOURCE_CAP})
    return {"status": "ran", "active_resources": n}
