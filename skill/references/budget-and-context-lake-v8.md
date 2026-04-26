# Budget and Context Lake v8

Large-budget mode is intended for 1M+ effective context and 10M-20M+ campaign-level work through externalized state, not one giant prompt.

## Contract

- Never terminate merely because local token context is full.
- After each phase, write a shard and a handoff capsule.
- Use branch-local candidate packs, not one mutable draft.
- Preserve failed paths because future repairs often reuse their error signatures.
- For a hard theorem, assume 24h+ is acceptable unless the user gives a smaller cap.

## Context lake files

`context_lake/index.json` contains compact records:

```json
{"id":"notation-0001","stage":"notation","kind":"ledger","path":"context_lake/shards/notation-0001.md","summary":"Ring variables and nonzero denominator assumptions fixed.","tokens_est":900,"depends_on":[]}
```

Shard kinds: problem, notation, knowledge, blueprint, line_map, candidate, failure, audit, handoff, memory_summary.

## Handoff capsule

A handoff capsule must contain: current theorem signature, accepted artifacts, open obligations, blocked branches, exact next commands, and hard vetoes still active.

## Minimum quotas

For research/frontier mode, before claiming blocked, document at least: 3 theorem variants, 3 library search passes, 2 skeleton decompositions, 8 lemma-sprint candidates for the hardest leaf when possible, 1 red-team pass, and 1 replay attempt. If tools are unavailable, write task cards with the missing command and expected evidence.
