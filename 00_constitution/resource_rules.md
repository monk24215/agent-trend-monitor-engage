# RESOURCE CURATION — Layer 0 (immutable rules)
#
# A "resource" = a source the Assessor gathers current_signals from
# (feed, query, API, list). Distinct from a "pattern" (a rule about good topics).
#
# Resources earn their place exactly like patterns do — same lifecycle, same
# anti-cruft cap — but curation runs on a SLOWER clock, not daily.

## Cadence
- Daily loop does NOT curate resources. It only USES the promoted set.
- Curation runs at a convenient, regular point: default WEEKLY (day: Monday).
- Rationale: a resource needs several days of signal before it can be judged.
  Daily curation would thrash the list and waste calls.

## Lifecycle (never delete — only move)
observed -> candidate -> validated -> promoted -> (demoted -> archived)
- candidate:  a newly-found source, proposed but not yet trusted. Not in hot path.
- validated:  its signals reached the daily output and performed >= N times.  N = 3
- promoted:   Assessor is allowed to gather from it.
- demoted:    its signals underperformed / went stale M times.  M = 3 -> archived
- archived:   kept forever with reason + pointer. NEVER deleted.

## Anti-cruft cap
- AT MOST 8 promoted resources at once.
- To promote a 9th, the weakest promoted resource MUST be demoted first.

## "Find the best resources" (candidate discovery)
- The weekly pass MAY propose new candidate resources.
- New sources ALWAYS enter as `candidate`, never straight to promoted.
- This guarantees finding can never degrade live quality.

## Logging
Every resource move writes a build_log `pattern_move`-style entry with
object:"resource", from/to state, and the evidence numbers.
