# BODYGEN — Email Body-Copy Generator (Day 1)

A **delivery edge** for TMEA, not an engine agent. It reads `daily/*.json` and
expands each **derived** angle (topic x product) into a finished email body.
It never touches engine logic and never sends — output is always a **draft**
that still flows through your existing human gate.

## Why it lives outside `tmea/`
TMEA's constitution refuses long-form content; the engine writes headlines only.
Bodygen is a sibling edge — same pattern as `publisher.py` and `contentlog.py`.

## Install — drop both files into your package
```
cp bodygen.py bodygen_notion.py  <your-repo>/tmea/
```
They sit beside `core.py` / `llm.py` (they import `from .core` and `from .llm`).
`BODYGEN.md` goes at the repo root next to `OPERATING.md` (docs only).
No new dependencies: local generation uses what TMEA already imports; the Notion
push uses only the standard library. The `bodies/` output folder is created on
first run — add `bodies/` to `.gitignore`.

## Daily use
```
python -m tmea.bodygen                 # newest day -> bodies/<run_id>.json
python -m tmea.bodygen --run 2026-08-16
python -m tmea.bodygen --only deriv-2026-08-16-01
python -m tmea.bodygen --push-notion   # also upsert bodies into the tracker
```
Source of truth is `bodies/<run_id>.json`. Notion is a downstream push.

## Configuration (all optional, all env vars)
| Var | Default | Purpose |
|---|---|---|
| `BODYGEN_MODEL` | `claude-sonnet-4-6` | model tier for body copy |
| `BODYGEN_MAX_TOKENS` | `1200` | longer than headlines; bodies need room |
| `BODYGEN_POSTURE` | `strict` | `strict` (honest, CAN-SPAM aware) or `persuasive` |
| `NOTION_TOKEN` | — | required only for `--push-notion` (composer's own secret) |
| `NOTION_DB_ID` | — | the Email Campaign Tracker (composer's own secret) |

With no `ANTHROPIC_API_KEY`, bodygen runs on TMEA's deterministic **mock** —
the whole pipeline flows with zero credentials, identical shapes to real output.

## Compliance (strict default)
- Prompt spine forbids fabricated facts, stats, scarcity, deadlines, guarantees.
- A regex tripwire scans every body; hits go into `compliance_flags` and into
  the Notion **Agent Notes** with a WARNING so a human sees them.
- The CAN-SPAM footer (unsubscribe + physical address) is injected by Constant
  Contact at send time — bodygen never fabricates one.

## How it fits the pipeline
```
TMEA run -> daily/<id>.json -> BODYGEN -> bodies/<id>.json
                                   \--(--push-notion)--> tracker "Body Copy" (Status=draft)
                                                              \--> composer --> CC DRAFT
                                                                        \--> human review & send
```
Bodygen fills the **Body Copy** field the composer already checks — the composer
skips rows with empty bodies, so this is the piece that unblocks the compose loop
(Day 2). Nothing here crosses the `DRAFT_ONLY` wall.

## Notion contract — matches the real Email Campaign Tracker
Verified against `composer/src/lib/notion.js`:
- Writes `Subject Line` (title), `Body Copy`, `Preheader`, `Category`,
  `Send Date`, `Status`='draft', and `Agent Notes`.
- Endpoint `POST /data_sources/{NOTION_DB_ID}/query`, Notion-Version `2025-09-03`,
  parent `data_source_id` — same as the composer.
- **No new property required.** Idempotency is keyed on `Subject Line`: an
  existing row with non-empty Body Copy is left alone (human edits never
  clobbered); an existing empty row is updated; no match creates a new draft row.
- Reuses the composer's `NOTION_TOKEN` / `NOTION_DB_ID` — no second secret.

## Verified before ship
- Full mock run over a realistic `daily/*.json` -> emails with correct shapes.
- Preheader split works, and degrades gracefully when absent.
- Compliance tripwire fires on fabricated urgency/guarantees, silent on clean copy.
- Notion push fails loudly (never silently drops copy) when creds are missing.
- Upsert verified on all three branches: create, update-empty, skip-has-body —
  against the composer's exact field names, endpoint, and API version.

## Next (Day 2)
Wire `python -m tmea.bodygen --push-notion` into the daily job right after
`python -m tmea.run`, then let the composer pick up the now-populated rows.
Keep the content-log decision gate manual until the Day 4 deliverability ramp
is green.
