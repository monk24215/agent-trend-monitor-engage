"""Agent 1 — ASSESSOR.
Scores each signal for audience relevance using a HYBRID, transparent method:
a deterministic baseline (keyword + authority matching) that the model then
adjusts. Both halves are logged, so every score is explainable and the ranking
degrades gracefully if the model is unavailable.

Input : signals dict (validated), domain_reference, persona
Output: signals with .score and .score_breakdown, ranked high->low
"""
from __future__ import annotations
import os, re
from .core import CONSTITUTION, read_yaml
from .llm import llm


def _load_reference():
    ref = {}
    p = os.path.join(CONSTITUTION, "domain_reference.yaml")
    if os.path.exists(p):
        ref = read_yaml(p)
    return ref


def _baseline_score(signal: dict, authorities: list[str]) -> tuple[float, dict]:
    """Deterministic, explainable. Returns (score 0..1, breakdown)."""
    text = (signal.get("headline_or_topic", "") + " " +
            signal.get("raw_note", "") + " " +
            " ".join(signal.get("tags", []))).lower()
    breakdown = {}

    # authority mention bonus
    auth_hits = [a for a in authorities if a.lower() in text]
    auth_bonus = min(0.3, 0.15 * len(auth_hits))
    breakdown["authority_hits"] = auth_hits
    breakdown["authority_bonus"] = auth_bonus

    # tag richness (a signal that arrived categorized is a bit more usable)
    tag_bonus = min(0.2, 0.05 * len(signal.get("tags", [])))
    breakdown["tag_bonus"] = tag_bonus

    # base presence
    base = 0.4 if signal.get("headline_or_topic") else 0.0
    breakdown["base"] = base

    score = round(min(1.0, base + auth_bonus + tag_bonus), 3)
    breakdown["baseline_total"] = score
    return score, breakdown


def _model_adjust(signal: dict, baseline: float, ctx) -> tuple[float, str]:
    """Model nudges the baseline. Kept small and bounded so the deterministic
    spine dominates; the model refines, never overrides wholesale."""
    prompt = (
        "You score survival/bushcraft topic relevance for a preparedness audience.\n"
        f"Baseline score (0-1): {baseline}\n"
        f"Topic: {signal.get('headline_or_topic','')}\n"
        "Reply with only a signed adjustment between -0.2 and 0.2 (e.g. +0.1)."
    )
    raw = llm(prompt, purpose="assessor_adjust", ctx=ctx)
    adj = 0.0
    try:
        m = re.search(r"[-+]?\d*\.?\d+", raw)
        if m:
            adj = max(-0.2, min(0.2, float(m.group())))
    except Exception:
        adj = 0.0
    return adj, raw


def assess(signals_doc: dict, ctx) -> list[dict]:
    ref = _load_reference()
    authorities = [a.get("name", "") for a in ref.get("authorities", [])] if isinstance(ref.get("authorities"), list) else []

    scored = []
    for sig in signals_doc.get("signals", []):
        base, breakdown = _baseline_score(sig, authorities)
        adj, raw = _model_adjust(sig, base, ctx)
        final = round(max(0.0, min(1.0, base + adj)), 3)
        breakdown["model_adjustment"] = adj
        breakdown["final"] = final
        s = dict(sig)
        s["score"] = final
        s["score_breakdown"] = breakdown
        scored.append(s)

    scored.sort(key=lambda x: x["score"], reverse=True)
    ctx.log("assess", {"count": len(scored),
                       "ranked": [{"id": s["id"], "score": s["score"]} for s in scored]})
    return scored
