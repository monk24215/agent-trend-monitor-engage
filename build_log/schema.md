# BUILD LOG — append-only. One JSONL line per event. Never edit past lines.

Event types: run_start, assess, categorize, generate, document, pattern_move, error, gate_change

Line schema:
{ "ts": ISO8601, "type": "...", "run_id": "YYYY-MM-DD",
  "detail": { ... type-specific ... } }

pattern_move detail: { "pattern_id","from","to","evidence":{...} }
generate  detail: { "discovery":[ids],"derived":[ids],"scores":{...} }
error     detail: { "stage","message" }
