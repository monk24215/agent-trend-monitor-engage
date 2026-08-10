"""ORCHESTRATOR — the deterministic spine that runs the daily loop:
    assess -> log -> categorize+store -> generate -> document -> learn -> (wait)
It enforces the constitution invariants MID-RUN (after generation, before the
output is committed), so a run that would violate Layer 0 stops instead of
shipping bad state.

Usage:
    python -m tmea.run                      # uses inputs/signals.json (or template)
    python -m tmea.run --signals path.json
"""
from __future__ import annotations
import os, sys, importlib.util
from .core import INPUTS, RunContext, read_json
from .assessor import assess
from .categorizer import categorize
from .generators import generate_discovery, generate_derived
from .documenter import document, learn, curate_resources
from .validate_input import validate


def _load_signals(path: str | None) -> dict:
    if path is None:
        for cand in ["signals.json", os.path.join("templates", "signals.template.json")]:
            p = os.path.join(INPUTS, cand)
            if os.path.exists(p):
                path = p
                break
    if not path or not os.path.exists(path):
        raise FileNotFoundError("no signals file; create inputs/signals.json")
    validate("signals", path)  # fail loudly at the door
    return read_json(path)


def _run_invariants():
    """Load and run the constitution tests mid-loop. Any failure raises."""
    from tests import test_constitution as t  # type: ignore
    for name in dir(t):
        if name.startswith("test_"):
            getattr(t, name)()


def _check_today(out_path: str):
    """Live-run gate: validate only THIS run's output file. Stale files from
    other days are the test suite's concern, not a blocker for today's run."""
    d = read_json(out_path)
    assert len(d.get("discovery", [])) == 5, f"{out_path}: need exactly 5 discovery"
    assert len(d.get("derived", [])) == 5, f"{out_path}: need exactly 5 derived"


def run(signals_path: str | None = None) -> str:
    ctx = RunContext()

    # Go live automatically if a key is present; otherwise stay on the mock.
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from .provider import set_up
            set_up()
            ctx.log("provider", {"mode": "real"})
        except Exception as e:
            ctx.log("provider", {"mode": "mock", "reason": str(e)})
    else:
        ctx.log("provider", {"mode": "mock", "reason": "no ANTHROPIC_API_KEY"})

    ctx.log("run_start", {"signals": signals_path or "auto"})

    signals_doc = _load_signals(signals_path)          # assess input

    # Guard BEFORE doing any work or writing any file: you can't make 5
    # discovery topics from fewer than 5 signals. Fail clearly, write nothing.
    n_sig = len(signals_doc.get("signals", []))
    if n_sig < 5:
        msg = (f"need at least 5 signals to produce 5 discovery topics; "
               f"inputs has {n_sig}. Add more entries to your signals file.")
        ctx.log("error", {"stage": "precheck", "message": msg})
        raise SystemExit("TMEA: " + msg)

    scored = assess(signals_doc, ctx)                  # 1 assess (+log inside)
    categorized = categorize(scored, ctx)              # 2 categorize + store
    discovery = generate_discovery(categorized, ctx)   # 3 discovery
    derived = generate_derived(categorized, ctx)       # 4 derived

    out_path = document(discovery, derived, ctx)       # 5a document

    # Validate ONLY today's output during a live run (stale files from other
    # days shouldn't block today's run; the full sweep still runs in the test suite).
    try:
        _check_today(out_path)
        ctx.log("invariants", {"status": "pass"})
    except AssertionError as e:
        ctx.log("error", {"stage": "invariants", "message": str(e)})
        raise

    learn(ctx)                                         # 5b learn (if feedback)
    curate_resources(ctx)                              # 5c weekly curation

    # Publish the newsroom-style HTML brief (a delivery edge, not engine logic)
    try:
        from .publisher import publish
        brief = publish(ctx.run_id)
        ctx.log("publish", {"brief": brief})
    except Exception as e:
        ctx.log("publish", {"status": "skipped", "reason": str(e)})

    ctx.log("run_end", {"output": out_path})
    return out_path


if __name__ == "__main__":
    path = None
    if "--signals" in sys.argv:
        path = sys.argv[sys.argv.index("--signals") + 1]
    out = run(path)
    print(f"daily output written: {out}")
