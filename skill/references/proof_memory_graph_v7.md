# Proof-memory graph

Long formalization campaigns require external memory.  Do not rely on the chat context as the only store.

## Event types

Use `assets/schemas/proof_memory_event_v7.schema.json` for machine-readable records.

Recommended relations:

- `defines`: symbol or structure definition;
- `depends_on`: dependency edge;
- `derives`: proved lemma relation;
- `updates`: corrected statement or proof;
- `contradicts`: counterexample or failed hypothesis;
- `repairs`: compiler-error fix;
- `replaces`: superseded artifact;
- `supports`: evidence for a decision.

## Memory policy

New facts do not overwrite old facts silently.  They create `updates` or `replaces` edges.  Contradictions stay visible until resolved by a new gate decision.

## Retrieval policy

Before a lemma sprint, retrieve by theorem name, involved symbols, failed error class, and nearby dependencies.  Prefer recent verified repairs over old unverified sketches.
