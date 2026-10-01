---
name: mathprove-skill
description: A mathematical research workbench for sustained proof projects, literature reuse, lemma exploration, counterexamples, symbolic computation and optional Lean verification. Keep research notes and unfinished work resumable, use current compatible Lean/mathlib, and distinguish proved results from conjectures and computational evidence.
---

# MathProve — mathematical research workbench

Advance the mathematical problem. This skill is a workbench, not a software supply-chain audit or a release-approval system. Use the user's language and notation.

## Begin or resume

Read the existing problem, assumptions, notation, proof attempts and relevant artifacts before choosing the next action. Keep hypotheses and the intended conclusion explicit. Correct the statement openly when the mathematics requires it; do not silently prove a weaker theorem.

For a sustained project, the optional portable controller provides notes, lemma tasks, checkpoints and evidence records. Use `python <skill-root>/scripts/mathprove.py --root <research-root> doctor`, then `init`, `list` or `status`. Read `references/v9/operations.md` only when using those commands. A small self-contained proof does not need a database or all six stages.

If an existing CoMath service is already the workbench, read `references/v9/comath-backed.md` and discover its current tools. Do not create a second database for the same project.

## Local execution

Local execution is the default and is allowed. Run mathematical computations, Python scripts and Lean/Lake commands directly on the host.

Do not require Docker, Podman, a virtual machine, or a container sandbox as a prerequisite. Host permissions remain unchanged.

If a tool is missing, report the specific local dependency rather than require a container installation. Use the optional legacy `scripts/docker_runner.py` only when the user explicitly chooses Docker execution.

## Research database

TriviumDB is the research database dependency for document records, user-provided vectors and relationships. Install `requirements-db.txt` with the Python interpreter used for database commands; the dependency is unpinned, and local source installations are valid. Use a Python version supported by the installed TriviumDB package rather than force an incompatible interpreter.

Use `db-init`, `db-put`, `db-get`, `db-query` and `db-link` through the controller; see `references/v9/operations.md`. Supply actual vectors, not invented embeddings. Records retain their run and goal revision. SQLite continues to store tasks, leases, sessions and workflow state; research database records do not become proof evidence automatically. `doctor` reports the actual dependency environment. Missing TriviumDB does not block ordinary mathematical work or the SQLite controller.

## Research method

- Define objects, quantifiers, assumptions and conventions. Separate strict proofs, conditional lemmas, conjectures, physical intuition and finite/numerical evidence.
- Prefer the next useful mathematical action: a reusable library theorem, a small exact calculation, a boundary case, a counterexample, a compiler experiment or a missing lemma.
- Maintain a small lemma dependency graph and record failed routes with their actual obstruction. Compare genuinely different approaches when that helps; do not manufacture reviews or parallel roles merely to satisfy a checklist.
- Reuse sources only after checking their hypotheses. A missing search result is not a novelty claim. Surface gaps rather than hide them behind a score or a successful unrelated calculation.
- Use only the coordinator and specialist roles needed by the current problem. Shared role guidance is in `assets/v9/roles/`; subagents are optional, and sequential passes are not independent reviews.

## Lean and mathlib

Use the latest mutually compatible Lean/mathlib environment. For mathlib projects, follow current mathlib's toolchain requirements rather than independently forcing an incompatible Lean release. Refresh dependencies through normal Lake commands when preparing or updating the project; keep using the installed cache during research.

Do not freeze versions, require exact dependency commits, insist on a pre-existing `lake-manifest.json`, hash files or executables, or request approval again merely because the environment or a note changed. Lake may generate its ordinary toolchain/manifest files; those are build metadata, not MathProve acceptance locks. Local path dependencies are valid.

For formal work, `verify <run>` runs `lake build` in the actual project, reuses `.lake`, checks the requested declaration against the exact `expected_type`, and reports its axiom dependencies. Ordinary compilation is part of the requested research task; `--allow-build` remains an optional legacy flag, not a second approval gate. Legitimate macros and metaprogramming are not rejected by blanket lexical rules.

A successful build containing `sorry`, a custom unsupported axiom, or a theorem with the wrong type is not a proof of the requested claim. If Lean is unavailable, continue the mathematical research and clearly label formal checking as pending. Never call an unperformed check successful.

## Notes and stopping

Use ordinary revision identifiers to keep work attached to the right mathematical goal. Existing `spec_hash` field names are compatibility aliases for those identifiers, not content hashes. Edit and improve working notes normally; register a new result or withdraw an obsolete claim when its mathematical meaning changes.

Review is a mathematical judgment, not a mandatory human-signature ceremony. The optional controller's `spec → plan → candidate → refutation → verify → release` organizes recorded work; its labels do not establish mathematical truth or novelty. Read `references/v9/protocol.md` for the actual checks, not an engineering audit procedure.

Checkpoint useful progress on interruption or a real obstruction, state the remaining obligation and the highest-value next action, and continue when new evidence or resources justify it. Do not impose token-consumption targets, fixed proof routes, repeated approvals, hash-validation detours or an endless prove-until-done loop.

## Host integration

Hooks and role presets are optional conveniences for resuming context. The controller does not call models or manage API keys. Host permissions remain unchanged; do not expose private research or credentials when publishing results.
