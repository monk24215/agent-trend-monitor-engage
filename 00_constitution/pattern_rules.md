# PATTERN LIFECYCLE — Layer 0 (immutable rules; the anti-cruft engine)

A "pattern" = a reusable rule the agent learned about what makes a good topic
for THIS audience (e.g. "how-to angles on product X outperform news recaps").

## Lifecycle (never delete — only move)
observed -> candidate -> validated -> promoted -> (demoted -> archived)

- observed:  noticed once. Logged, not used.
- candidate: seen enough to be worth testing. Not yet in the hot path.
- validated: beat baseline on performance_feedback >= N times.  N = 3
- promoted:  lives in 01_active_patterns/, actively shapes topic selection.
- demoted:   underperformed M times in a row.  M = 3  -> moved to 02_cold_store/
- archived:  demoted patterns kept forever with a pointer + reason. NEVER deleted.

## Anti-cruft caps (the whole point)
- 01_active_patterns/ holds AT MOST 12 promoted patterns.
- To promote a 13th, the weakest active pattern MUST be demoted first.
- This cap is a feature. It forces the agent to let go, per your efficiency goal.

## Hard requirement
Every promotion and demotion writes a build_log entry with: pattern_id, from_state,
to_state, evidence (the numbers), and timestamp. No silent forgetting.
