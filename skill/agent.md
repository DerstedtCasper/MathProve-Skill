# MathProve mathematical research practice

Use this skill to advance a mathematical research problem, not to audit a code supply chain. For an existing CoMath workbench, use `references/v9/comath-backed.md` and its currently discovered tools.

## Mathematical fidelity

State the objects, quantifiers, assumptions, conventions and intended conclusion. Preserve their meaning while exploring proofs. When a definition or hypothesis must change, record the mathematical reason and which lemmas it affects. Compare the actual Lean type with the intended theorem; successful elaboration of a different or vacuous statement is not enough.

Label each result: proved with identified evidence, conditional, conjectural, counterexample candidate, or computational observation. `sorry`, votes, confidence scores, finite searches and CAS outputs do not prove a general theorem. Check citations against primary sources; unread sources remain leads. Report failed checks honestly.

## Productive research

Choose a small discriminating next step: a boundary case, exact calculation, known library lemma, alternative route or compiler feedback. Record obstructions and abandoned approaches so resumption is useful. A task packet should contain only the relevant goal, assumptions, previous findings and requested output.

Use a lemma DAG when dependencies matter, and delegate only genuinely independent work. Do not activate every role, require a minimum context size or consume a prescribed token budget. A sequential change of role is not independent review.

## Environment

Local execution is the default and is allowed. Run mathematical computations, Python scripts and Lean/Lake commands directly on the host.

Do not require Docker, Podman, a virtual machine, or a container sandbox as a prerequisite. Host permissions remain unchanged.

If a tool is missing, report the specific local dependency rather than require a container installation. Use the optional legacy `scripts/docker_runner.py` only when the user explicitly chooses Docker execution.

Lean and mathlib should stay current and mutually compatible. Follow current mathlib's required Lean toolchain, normal Lake updates and the existing build cache. Do not require fixed versions, dependency commit locks, file hashes, binary fingerprints, cold rebuilds or repeated environment approvals. Record the tool versions actually used only when useful for understanding a result or an API change.

Normal compilation and evidence review are part of mathematical work. Preserve exact target-type and axiom checks, but do not prohibit legitimate macros, metaprogramming or local dependencies as a generic engineering precaution. Do not confuse a changed source file with a failed mathematical argument; recheck the affected mathematical claim when it actually changes.

TriviumDB stores research documents, supplied vectors and relationships; SQLite retains task, lease, session and workflow state. Install the unpinned `requirements-db.txt` with the interpreter used for `db-*` commands, or install current local TriviumDB sources. Follow its actual Python compatibility requirements, not a fixed package version. Use the controller to bind records to the run and revision; do not fabricate embeddings or treat database records as automatically accepted proof evidence. Read `references/v9/operations.md` for database commands.

## Artifacts and handoff

The portable controller uses revision IDs; old `spec_hash` keys are compatibility aliases, not hash checks. Return task_id, the current revision identifier, outcome (`candidate`, `blocked`, `refuted`, `no_progress`), a concise mathematical summary, next_action and artifact paths when using its task interface. A completed task is not automatically a proved theorem.

Edit working notes normally, keep useful checkpoints, and preserve unfinished obligations. Use the controller for its SQLite records so ordinary edits do not damage the database; this is a storage convention, not a research approval system. Review notes need no separate human acknowledgement or cryptographic snapshot.

Do not invent proofs, sources, executions or independent reviewers. Do not publish private work or credentials without the requested publication scope. Stop at a useful result, a real obstruction or the user's instruction, and explain what would make the next attempt worthwhile.
