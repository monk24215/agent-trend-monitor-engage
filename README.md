# Trend Monitor Engage Agent (`tmea`)

A single-purpose agent that stays simple in **purpose** but grows in
**capability** without accumulating cruft. Each day it produces:

- **5 discovery topics** — most interesting / informative / useful right now
- **5 derived topics** — current topics crossed with our products/services and
  what the audience values about them

## Architecture: fixed core vs. mutable layer

| Layer | Dir | Mutability |
|-------|-----|-----------|
| 0 — Constitution | `00_constitution/` | immutable; human-edited only |
| 1 — Active | `01_active_patterns/` | curated, capped (anti-cruft) |
| 2 — Cold store | `02_cold_store/` | append-only archive; never deleted |
| — History | `build_log/` | append-only event log |
| — Output | `daily/` | one file per day (5 + 5) |
| — Tests | `tests/` | constitution invariants, run between sections |
| — Package | `tmea/` | the engine (orchestrator + 5 agents) |

Three governed objects share ONE lifecycle
(`observed → candidate → validated → promoted → demoted → archived`) and ONE
discipline (a hard cap forces letting go before taking on more):

- **patterns** — rules about what makes a good topic (`pattern_rules.md`, cap 12)
- **resources** — where signals come from (`resource_rules.md`, cap 8, weekly curation)
- **engagement events** — time-boxed priority overrides that expire (Layer 1)

## The pipeline — 5 process agents

1. **Assessor** — score incoming signals for audience relevance *(model call)*
2. **Categorizer** — categorize + store signals, match against patterns
3. **Discovery Generator** — top signals → 5 discovery headlines *(model call)*
4. **Derivation Generator** — signals × product catalog → 5 derived headlines *(model call)*
5. **Documenter/Learner** — write daily file, append log, run promotion/demotion
   gate; weekly, curate resources

Daily loop: `assess → log → categorize+store → generate → document → wait`

## Inputs contract (`inputs/`)

All three feeds share one discipline: a JSON template you can fill by hand today,
a JSON Schema that validates it, and one validator that fails loudly at the door.
Same shapes work when an API emits them later — nothing downstream changes.

| Kind | Template | Feeds |
|------|----------|-------|
| `signals` | `inputs/templates/signals.template.json` | the Assessor (current signals) |
| `feedback` | `inputs/templates/feedback.template.json` | the Learner (closes the loop) |
| `product_catalog` | `inputs/templates/product_catalog.template.json` | the Derivation Generator |

Validate before a run: `python -m tmea.validate_input signals inputs/signals.json`
(Install the `validate` extra for full schema checks; otherwise a zero-dep
minimal check runs.)

## Status / blockers
Scaffold + constitution finalized. Two inputs still needed before the pipeline
runs on real data instead of stubs:

1. **Current-signals source** — the seed resource list the Assessor gathers from.
2. **Performance-feedback source** — what tells the agent which past topics landed.
