# COLD STORE — Layer 2 (archive; append-only, NEVER delete)

Demoted patterns, expired engagement events, and retired resources land here
with a pointer back to their last active state and the reason for demotion.

Files:
- patterns.yaml    — archived patterns (from 01_active_patterns)
- resources.yaml   — archived/candidate resources (from resource_registry)
- events.yaml      — expired engagement events

Nothing is ever removed from these files. This is the audit trail that lets
you diagnose why the agent's behavior changed over time.
