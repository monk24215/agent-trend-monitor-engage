"""Agents 3 & 4 — GENERATORS.
Kept separate on purpose: discovery ("what's hot") and derivation ("what's hot
x what we sell") have different logic, and keeping them apart preserves the
quality signal for learning which KIND of topic lands.

Both call the model through the one llm() seam, and both honor active engagement
events (time-boxed priority tilts) applied as a bounded weight, never a takeover.
"""
from __future__ import annotations
import os, re
from .core import ACTIVE, INPUTS, read_yaml, read_json
from .llm import llm

# Appended to every generator prompt so the model returns ONLY the headline.
_ONLY = (" Output requirement: reply with ONLY the single headline text on one "
         "line. No markdown, no asterisks, no quotes, no '#', no explanation, "
         "no 'why this works', nothing before or after the headline.")


def _clean_headline(raw: str) -> str:
    """Safety net: strip markdown/preamble even if the model over-explains.
    Takes the first substantive line and removes stray formatting."""
    text = raw.strip()
    _labels = ("headline", "proposed headline", "title", "why this works")
    # if the model returned an essay, keep only the first non-empty content line
    for line in text.splitlines():
        s = line.strip()
        if not s or set(s) <= set("-#*_ "):   # skip blank / rule / heading-only lines
            continue
        s = re.sub(r"^[#>\-\*\s]+", "", s)      # leading markdown tokens
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)  # inline bold
        s = s.strip().strip('"').strip("*").strip('"').strip()  # stray quotes both ends
        # skip pure label lines ("Headline:", "Proposed Headline:", etc.)
        if s.rstrip(":").strip().lower() in _labels:
            continue
        if s:
            return s
    return text.strip().strip('"')


def _active_events():
    p = os.path.join(ACTIVE, "engagement_events.yaml")
    if not os.path.exists(p):
        return []
    doc = read_yaml(p)
    evs = doc.get("events", [])
    return evs if isinstance(evs, list) else []


def _event_tilt_note(events) -> str:
    if not events:
        return ""
    goals = "; ".join(e.get("goal", "") for e in events if isinstance(e, dict))
    return f" Bias gently toward these active goals (do not let them dominate): {goals}." if goals else ""


def generate_discovery(categorized: list[dict], ctx, n: int = 5) -> list[dict]:
    top = categorized[:max(n * 2, n)]  # candidate pool = top-scored
    tilt = _event_tilt_note(_active_events())
    out = []
    for i, sig in enumerate(top[:n]):
        prompt = (
            "Write ONE punchy, informative headline for a survival/preparedness "
            "audience based on this topic. No clickbait, no fabricated facts.\n"
            f"Topic: {sig.get('headline_or_topic','')}\n"
            f"Category: {sig.get('category','')}." + tilt + _ONLY
        )
        headline = _clean_headline(llm(prompt, purpose="discovery_headline", ctx=ctx))
        out.append({
            "id": f"disc-{ctx.run_id}-{i+1:02d}",
            "kind": "discovery",
            "headline": headline,
            "category": sig.get("category"),
            "source_signals": [sig.get("id")],
            "score": sig.get("score"),
        })
    ctx.log("generate", {"half": "discovery", "ids": [t["id"] for t in out]})
    return out


def _load_catalog():
    # prefer a live inputs/product_catalog.json, else the template
    for cand in ["product_catalog.json",
                 os.path.join("templates", "product_catalog.template.json")]:
        p = os.path.join(INPUTS, cand)
        if os.path.exists(p):
            return read_json(p).get("products", [])
    return []


def _match_products(sig: dict, products: list[dict]) -> list[dict]:
    hay = (sig.get("headline_or_topic", "") + " " +
           " ".join(sig.get("tags", []))).lower()
    hits = []
    for p in products:
        if not p.get("active", True):
            continue
        kws = [k.lower() for k in p.get("keywords", [])]
        if any(k in hay for k in kws) or not kws:
            hits.append(p)
    return hits


def _score_product(sig: dict, product: dict) -> int:
    """Count keyword hits between a signal and a product. Higher = better fit."""
    hay = (sig.get("headline_or_topic", "") + " " +
           " ".join(sig.get("tags", []))).lower()
    kws = [k.lower() for k in product.get("keywords", [])]
    return sum(1 for k in kws if k in hay)


def _best_product(sig: dict, products: list[dict], used_counts: dict) -> dict | None:
    """Pick the product that best fits this signal, with a light nudge away from
    products already used a lot today — so the day's derived set shows variety
    instead of clumping on one broad-keyword product. Fit still wins; the nudge
    only breaks ties and discourages runaway repetition."""
    candidates = [p for p in products if p.get("active", True)]
    if not candidates:
        return None
    best, best_key = None, None
    for p in candidates:
        fit = _score_product(sig, p)
        penalty = used_counts.get(p.get("id"), 0) * 0.5  # gentle anti-repeat
        key = fit - penalty
        if best_key is None or key > best_key:
            best, best_key = p, key
    # require at least a weak fit unless nothing fits at all
    if _score_product(sig, best) == 0:
        # fall back to least-used product so we still vary
        best = min(candidates, key=lambda p: used_counts.get(p.get("id"), 0))
    return best


def generate_derived(categorized: list[dict], ctx, n: int = 5) -> list[dict]:
    products = _load_catalog()
    tilt = _event_tilt_note(_active_events())
    out = []
    used_counts: dict = {}
    pool = categorized[:]
    i = 0
    for sig in pool:
        if len(out) >= n:
            break
        prod = _best_product(sig, products, used_counts)
        if prod is None:
            continue
        used_counts[prod.get("id")] = used_counts.get(prod.get("id"), 0) + 1
        liked = "; ".join(prod.get("liked_aspects", [])[:2])
        prompt = (
            "Cross this current topic with our product to propose ONE headline "
            "that would interest the audience AND naturally relate to the product. "
            "Honest, not spammy.\n"
            f"Topic: {sig.get('headline_or_topic','')}\n"
            f"Product: {prod.get('name','')} — valued for: {liked}." + tilt + _ONLY
        )
        headline = _clean_headline(llm(prompt, purpose="derived_headline", ctx=ctx))
        out.append({
            "id": f"deriv-{ctx.run_id}-{i+1:02d}",
            "kind": "derived",
            "headline": headline,
            "category": sig.get("category"),
            "source_signals": [sig.get("id")],
            "product_id": prod.get("id"),
        })
        i += 1

    # if fewer than n matched, top up from highest-scored signals generically
    j = 0
    while len(out) < n and j < len(pool):
        sig = pool[j]; j += 1
        if any(sig.get("id") in d["source_signals"] for d in out):
            continue
        prod = products[0] if products else {"name": "our product", "liked_aspects": []}
        prompt = (
            "Propose ONE headline linking this topic to our product angle, honestly.\n"
            f"Topic: {sig.get('headline_or_topic','')}\nProduct: {prod.get('name','')}." + tilt + _ONLY
        )
        headline = _clean_headline(llm(prompt, purpose="derived_headline_topup", ctx=ctx))
        out.append({
            "id": f"deriv-{ctx.run_id}-{len(out)+1:02d}",
            "kind": "derived",
            "headline": headline,
            "category": sig.get("category"),
            "source_signals": [sig.get("id")],
            "product_id": prod.get("id", None),
        })

    ctx.log("generate", {"half": "derived", "ids": [t["id"] for t in out]})
    return out
