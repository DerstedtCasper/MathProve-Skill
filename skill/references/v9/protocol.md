# MathProve research records and verification

This is a mathematical workbench. Its optional local controller records goals, tasks, notes, counterexamples and verification results; it is not an engineering audit or approval system.

## Research state

`.mathprove/state.sqlite3` stores task metadata. `.mathprove/objects` keeps registered evidence copies identified by ordinary object IDs; `.mathprove/checkpoints` contains resumable summaries; `.mathprove/replays` contains compilation logs. Working artifacts stay in the research workspace.

Each mathematical goal has a revision ID such as `paper1:2`. The legacy `spec_hash` field carries this ID for compatibility with existing task JSON; it is not a content digest. A changed goal requires an explicit `revise` so tasks are not accidentally attached to a different theorem. Working notes and lemma drafts can be edited normally. Their byte changes do not cause hash failures or automatic reapproval. Registered copies remain historical; register the revised claim when its mathematical meaning changes.

The controller checks that referenced files exist and that required mathematical records are readable. It does not compare file, dependency, executable, log or event hashes. Old database column names remain readable without migrating or erasing research history.

## Optional workflow stages

| Stage | Mathematical purpose |
|---|---|
| spec | Compare the intended statement, assumptions and formal type |
| plan | Record an acyclic lemma graph and checked sources or an elementary-task explanation |
| candidate | Keep a candidate argument and visible unresolved objections |
| refutation | Record adverse tests, boundary cases and unresolved counterexamples |
| verify | Integrate research findings, or run Lean on the exact target |
| release | Summarize the recorded result and remaining limits; no extra human-signature gate |

These stages help a sustained project resume. A small proof need not initialize them. Reviewer names and result labels record mathematical judgments; they do not authenticate an institution, establish novelty or turn an informal argument into a formal proof.

## Lean and mathlib

Use current mutually compatible Lean/mathlib. Prepare or update a project with normal Lake commands, using current mathlib's required Lean toolchain. Do not independently replace that toolchain with an incompatible release. Existing versioned `lean-toolchain` or generated `lake-manifest.json` files are normal Lake metadata, not a requirement to freeze old versions forever. `stable`, `nightly`, moving branches, registry packages and local path dependencies are not rejected by MathProve.

`verify <run>` executes `lake build` in the actual project and reuses `.lake`. It then generates a small audit theorem with the requested `expected_type`, applies the specified declaration, runs `lake env lean`, and reads its axiom report. No cold project copy, source fingerprint, dependency Git status, binary hash or log hash is required. Ordinary compilation does not need a repeated `--allow-build` acknowledgement.

The result records the full mathematical specification, actual Lean/Lake versions, command exit codes, logs, target-type result and axioms. `sorryAx` identifies an incomplete proof. Axiom dependencies outside `propext`, `Classical.choice`, `Quot.sound` are reported rather than treated as an unconditional proof. Legitimate macros, `elab`, `native_decide`, local libraries and other normal research techniques are not forbidden by a blanket source scan.

A result remains a historical record of the target that was checked. If the target or proof changes, run Lean again before claiming that the new result has been checked; the workbench does not enforce this through file hashes. A failed or absent actual check is not a formal success. Missing Lean does not stop informal research, literature work, CAS experiments or proof planning.

## Hooks, review and collaboration

Hooks restore small context summaries and save checkpoints; they never compile or call a model. They retain lightweight metadata rather than raw private commands, tool responses or cryptographic fingerprints. Review is an ordinary mathematical note, not a host-only signature ceremony. SQLite writes still go through the controller to avoid corrupting saved work.

Keep actual assumptions and unresolved objections visible. Distinguish independent review from sequential role passes. Preserve useful failure notes, respect the user's stop request, and avoid mandatory token quotas, repeated approvals and hash-validation detours. Host permissions and publication scope are unchanged.
