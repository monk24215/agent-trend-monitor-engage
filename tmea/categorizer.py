"""Agent 2 — CATEGORIZER.
Pure deterministic. Assigns a category to each scored signal (from tags/keywords)
and stores the day's assessed signals. No model call — this is routing, not
judgment.

Input : ranked scored signals, ctx
Output: same signals with .category; also persisted under daily/store/
"""
from __future__ import annotations
import os
from .core import DAILY, write_json

# simple, extendable category map. Order matters: first match wins.
CATEGORY_RULES = [
    ("gear",        {"gear", "kit", "knife", "pack", "boots", "blanket", "sleep"}),
    ("shelter",     {"shelter", "tent", "tarp", "cabin", "bivvy"}),
    ("fire",        {"fire", "tinder", "ferro", "ignition"}),
    ("water",       {"water", "filter", "purif", "hydrat"}),
    ("food",        {"food", "forage", "hunt", "trap", "storage", "garden"}),
    ("first-aid",   {"first aid", "medical", "wound", "trauma"}),
    ("skills",      {"knot", "navigation", "bushcraft", "primitive", "skill"}),
    ("power",       {"power", "solar", "generator", "energy", "grid"}),
    ("news",        {"news", "alert", "warning", "recall"}),
]


def _categorize_one(signal: dict) -> str:
    hay = (signal.get("headline_or_topic", "") + " " +
           " ".join(signal.get("tags", []))).lower()
    for cat, terms in CATEGORY_RULES:
        if any(t in hay for t in terms):
            return cat
    return "uncategorized"


def categorize(scored_signals: list[dict], ctx) -> list[dict]:
    out = []
    counts: dict[str, int] = {}
    for s in scored_signals:
        cat = _categorize_one(s)
        s = dict(s)
        s["category"] = cat
        counts[cat] = counts.get(cat, 0) + 1
        out.append(s)

    store_path = os.path.join(DAILY, "store", f"{ctx.run_id}.json")
    write_json(store_path, {"run_id": ctx.run_id, "signals": out})
    ctx.log("categorize", {"counts": counts, "stored": store_path})
    return out
