"""BODYGEN — email body-copy generator. A DELIVERY EDGE, not an engine agent.

Why this lives outside the engine
----------------------------------
TMEA's constitution refuses to write long-form content (see
00_constitution/purpose.md and the note in tmea/contentlog.py). The engine
produces headlines + angles only. This module is a *sibling* delivery edge —
exactly like publisher.py and contentlog.py — that READS daily/*.json and
expands a chosen angle into finished email copy. It never touches engine logic,
never imports an agent, and its output is a DRAFT that still flows through the
existing human gate (content_log.csv decision column → composer → CC draft).

It reuses the engine's own seams so nothing is reinvented:
  - tmea.core        for ROOT/DAILY/INPUTS, read_json/write_json, RunContext
  - tmea.llm.llm     the single model entry point (mock-safe, fully logged)
  - the catalog map   the same product_catalog.json the derivation agent uses

Model tier is configurable (BODYGEN_MODEL env var); compliance posture is
STRICT by default: honest, CAN-SPAM aware, no fabricated facts or urgency.

Run:
    python -m tmea.bodygen                # newest day, all promoted/pending derived rows
    python -m tmea.bodygen --run 2026-08-16
    python -m tmea.bodygen --only deriv-2026-08-16-01
    python -m tmea.bodygen --push-notion  # also upsert bodies into the Notion calendar
"""
from __future__ import annotations
import os
import re
import glob
import json
import argparse

from .core import ROOT, DAILY, INPUTS, read_json, write_json, RunContext, now_iso
from .llm import llm

# --------------------------------------------------------------------------
# Output locations (source of truth = local JSON; Notion is a downstream push)
# --------------------------------------------------------------------------
BODIES_DIR = os.path.join(ROOT, "bodies")          # one JSON per run day


# --------------------------------------------------------------------------
# Compliance spine — STRICT default. This text is appended to every prompt and
# is the constitutional posture of the copy engine. Mirrors the "_ONLY" tail
# pattern in tmea/generators.py so the model can't drift the format.
# --------------------------------------------------------------------------
_STRICT_RULES = """
NON-NEGOTIABLE WRITING RULES (a survival/preparedness email to a subscriber who
opted in):
- Be HONEST. Never fabricate facts, statistics, events, endorsements, scarcity,
  countdowns, or personal anecdotes. If you don't know a number, don't cite one.
- No fake urgency ("only 3 left", "expires at midnight") unless it is literally
  true and provided in the input. Do not invent deadlines.
- No health/financial/legal guarantees. No "cure", "guaranteed", "risk-free".
- Match the ONE product angle given. Do not add other offers or links.
- CAN-SPAM: write as commercial email. Do NOT invent an unsubscribe line or a
  physical address — the sending platform (Constant Contact) injects the
  compliant footer. Never tell the reader they cannot unsubscribe.
- Plain, direct, useful. Lead with value to the reader, not the sale.
- The affiliate link is a single call to action, placed once near the end.
"""

_PERSUASIVE_RULES = """
WRITING RULES (persuasive but TRUTHFUL marketing email):
- Persuasive, benefit-led, confident — but every claim must be TRUE and
  supportable. No fabricated facts, stats, scarcity, or deadlines.
- Match the ONE product angle. One call to action near the end.
- CAN-SPAM footer is injected by the platform — do not fabricate one.
"""


def _rules() -> str:
    posture = os.environ.get("BODYGEN_POSTURE", "strict").lower()
    return _PERSUASIVE_RULES if posture == "persuasive" else _STRICT_RULES


# --------------------------------------------------------------------------
# Model tier — configurable, mirrors tmea/provider.py's env-var discipline.
# bodygen asks llm() for MORE tokens than headlines, so it sets the model on
# the provider only if the caller wants a different tier than TMEA's default.
# The actual call still goes through tmea.llm.llm (mock-safe, fully logged).
# --------------------------------------------------------------------------
def _ensure_provider(ctx: RunContext) -> str:
    """Register the real Claude provider IF a key is present, using the
    BODYGEN_MODEL / BODYGEN_MAX_TOKENS env vars so body copy can use a
    different (longer, higher-quality) tier than the headline engine.
    Returns 'real' or 'mock'. Never raises — falls back to the mock."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        ctx.log("bodygen_provider", {"mode": "mock", "reason": "no ANTHROPIC_API_KEY"})
        return "mock"
    try:
        from anthropic import Anthropic
        from .llm import set_provider
        model = os.environ.get("BODYGEN_MODEL", "claude-sonnet-4-6")
        max_tokens = int(os.environ.get("BODYGEN_MAX_TOKENS", "1200"))
        client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

        def call(prompt: str) -> str:
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(
                b.text for b in resp.content if getattr(b, "type", "") == "text"
            ).strip()

        set_provider(call)
        ctx.log("bodygen_provider", {"mode": "real", "model": model,
                                     "max_tokens": max_tokens})
        return "real"
    except Exception as e:  # anthropic missing, bad key, etc. — stay on mock
        ctx.log("bodygen_provider", {"mode": "mock", "reason": str(e)})
        return "mock"


# --------------------------------------------------------------------------
# Catalog — same file the derivation agent reads (live, else template).
# --------------------------------------------------------------------------
def _load_catalog_map() -> dict:
    for cand in ["product_catalog.json",
                 os.path.join("templates", "product_catalog.template.json")]:
        p = os.path.join(INPUTS, cand)
        if os.path.exists(p):
            return {x["id"]: x for x in read_json(p).get("products", [])}
    return {}


# --------------------------------------------------------------------------
# Prompt construction + light cleanup
# --------------------------------------------------------------------------
def _build_prompt(item: dict, product: dict) -> str:
    headline = item.get("headline", "")
    category = item.get("category", "") or "preparedness"
    name = product.get("name", "our product")
    one_liner = product.get("one_liner", "")
    liked = ", ".join(product.get("liked_aspects", [])) or "quality and reliability"
    link = product.get("clickbank", {}).get("hoplink", "")

    return f"""Write a complete marketing email for a survival/preparedness
newsletter. The subject line / angle is already chosen — expand it into body copy.

ANGLE (subject): {headline}
CATEGORY: {category}
PRODUCT: {name}
PRODUCT ONE-LINER: {one_liner}
WHAT THE AUDIENCE VALUES ABOUT IT: {liked}
CALL-TO-ACTION LINK: {link or "[link injected at send time]"}

Return the email as plain text with a short preheader on the FIRST line prefixed
exactly "PREHEADER: ", then a blank line, then the body. 150-320 words. One clear
call to action using the link above, placed once near the end.
{_rules()}"""


_PREHEADER_RE = re.compile(r"^\s*PREHEADER:\s*(.*)$", re.IGNORECASE)


def _split_preheader(text: str) -> tuple[str, str]:
    """Pull the 'PREHEADER: ...' first line out; return (preheader, body)."""
    lines = text.strip().splitlines()
    preheader = ""
    if lines:
        m = _PREHEADER_RE.match(lines[0])
        if m:
            preheader = m.group(1).strip()
            lines = lines[1:]
    body = "\n".join(lines).strip()
    return preheader, body


# Cheap tripwire so a fabricated deadline/guarantee doesn't slip through silently.
_RED_FLAGS = [
    r"\bguarantee(d)?\b", r"\brisk[- ]free\b", r"\bexpires? (at|in|tonight|midnight)\b",
    r"\bonly \d+ (left|remaining)\b", r"\bcure(s|d)?\b", r"\b100% \w+\b",
]


def _compliance_flags(text: str) -> list[str]:
    hits = []
    low = text.lower()
    for pat in _RED_FLAGS:
        if re.search(pat, low):
            hits.append(pat)
    return hits


# --------------------------------------------------------------------------
# Core: generate one body from a daily item
# --------------------------------------------------------------------------
def generate_one(item: dict, catalog: dict, ctx: RunContext) -> dict:
    product = catalog.get(item.get("product_id", ""), {})
    prompt = _build_prompt(item, product)
    raw = llm(prompt, purpose="bodygen", ctx=ctx)
    preheader, body = _split_preheader(raw)
    flags = _compliance_flags(body)
    if flags:
        ctx.log("bodygen_flag", {"content_id": item.get("id"), "flags": flags})
    return {
        "content_id": item.get("id"),
        "headline": item.get("headline"),
        "subject": item.get("headline"),   # the angle IS the subject
        "preheader": preheader,
        "body": body,
        "product_id": item.get("product_id"),
        "category": item.get("category"),
        "compliance_flags": flags,          # non-empty => needs a human look
        "posture": os.environ.get("BODYGEN_POSTURE", "strict").lower(),
        "generated_at": now_iso(),
        "status": "draft",                  # ALWAYS draft — human gate is downstream
    }


# --------------------------------------------------------------------------
# Run over a day's derived items (derived = has a product angle to sell)
# --------------------------------------------------------------------------
def _latest_daily_path() -> str:
    files = sorted(glob.glob(os.path.join(DAILY, "*.json")))
    if not files:
        raise FileNotFoundError("no daily/*.json output to generate bodies from")
    return files[-1]


def generate_day(run_id: str | None = None, only: str | None = None) -> dict:
    ctx = RunContext(run_id)
    mode = _ensure_provider(ctx)
    path = os.path.join(DAILY, f"{run_id}.json") if run_id else _latest_daily_path()
    doc = read_json(path)
    rid = doc.get("run_id") or os.path.splitext(os.path.basename(path))[0]
    catalog = _load_catalog_map()

    # Only derived items carry a product angle worth writing a sales email for.
    items = doc.get("derived", [])
    if only:
        items = [it for it in items if it.get("id") == only]

    bodies = []
    for it in items:
        try:
            bodies.append(generate_one(it, catalog, ctx))
        except Exception as e:
            ctx.log("bodygen_error", {"content_id": it.get("id"), "error": str(e)})

    out = {"run_id": rid, "provider": mode, "count": len(bodies), "bodies": bodies}
    out_path = os.path.join(BODIES_DIR, f"{rid}.json")
    write_json(out_path, out)
    ctx.log("bodygen_write", {"path": out_path, "count": len(bodies)})
    return {"path": out_path, "run_id": rid, "count": len(bodies), "bodies": bodies}


def main():
    ap = argparse.ArgumentParser(description="TMEA body-copy generator (delivery edge)")
    ap.add_argument("--run", help="run_id / daily file to use (default: newest)")
    ap.add_argument("--only", help="only generate for this content_id")
    ap.add_argument("--push-notion", action="store_true",
                    help="also upsert bodies into the Notion calendar")
    args = ap.parse_args()

    result = generate_day(args.run, args.only)
    print(f"bodies written: {result['path']}  ({result['count']} emails)")

    if args.push_notion:
        from .bodygen_notion import push_bodies
        pushed = push_bodies(result["bodies"])
        print(f"notion upserts: {pushed}")


if __name__ == "__main__":
    main()
