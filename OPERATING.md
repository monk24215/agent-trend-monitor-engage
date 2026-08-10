# TMEA — Production Operating Sheet

The agent is built, tested, live, and in a clean public repo. This is everything
you need to run it. Nothing else to hold in your head.

## Daily use (the whole job)
1. Put today's trending topics into `inputs/signals.json` (>= 5, copy the shape
   from `inputs/templates/signals.template.json`).
2. Run:  `python -m tmea.run`
3. Read the result:  `daily/YYYY-MM-DD.json`  — 5 discovery + 5 derived headlines.

That's it. The model, scoring, categorizing, logging, and guards all run themselves.

## One-time setup on any machine
- `python bootstrap_tmea.py`         (writes the engine)
- `pip install anthropic`
- set `ANTHROPIC_API_KEY` in the environment
- create `inputs/signals.json` and `inputs/product_catalog.json` from templates

## To make derived headlines real (the one open content task)
Edit `inputs/product_catalog.json`: replace each `[PLACEHOLDER]` with a real
product — name, one_liner, liked_aspects (what the audience values), keywords,
and your ClickBank hoplink. This file is gitignored, so it stays private.

## Optional, whenever
- Tag outcomes in `inputs/feedback.json` (good/neutral/poor) to feed the
  learning loop over time.
- Cost trim: the assessor makes ~6 model calls/run on score nudges the
  deterministic baseline already handles. Removing them cuts cost ~40% with no
  quality loss. (Not required to operate.)

## Safety / repo
- Engine + templates are tracked and public. Live data (signals, products,
  output, logs) is gitignored and stays local. This is the correct shape.
- The API key lives only in an environment variable, never in a file.

## Health check
- `python tests/test_constitution.py`  — confirms the constitution invariants hold.
- `python -m tmea.provider`            — confirms the real model responds.
