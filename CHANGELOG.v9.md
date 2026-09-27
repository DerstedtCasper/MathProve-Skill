# 9.0.0-rc2 — 2026-09-27

Source-informed follow-up to the independent RC1 overlay. CoMath is pinned to e8e0182823b383cb228802c4d70f3309bf0a698c; MathProve to e4aaf6abec8c05bc5186d635b06b56152442380b. GitHub source reads succeeded; no full clones, full upstream builds or remote changes.

## Fixed

- Selected legacy v8 helper: reject mixed-stage/duplicate candidates and invalid thresholds; normalize nonfinite scores to zero; validate closed line-map DAGs with explicitly named external prerequisites; accept only literal true termination flags. These remain structural/ranking helpers, not proof certification.
- Repository overlay now refuses divergent pinned legacy source and touched dirty Git paths before writes; unrelated local changes remain untouched.
- Only actual context-emitting startup hook handlers receive additionalContextLimit, avoiding irrelevant event configuration.
- Retired the RC1 generic CoMath adaptations, whose portable role names and contracts did not match the actual registry and durable prompt path.
- Windows test fixtures now read UTF-8 release artifacts explicitly, use native absolute paths for MCP configuration, and skip symlink cases only when the current account cannot create them. This is test-harness portability only; it does not change the v9 protocol or runtime semantics.
- Repository text checkouts now use LF through `.gitattributes`, so the content-addressed v9 overlay remains reproducible when Windows Git has `core.autocrlf` enabled.

## Added

- Shared host-neutral mathematical research method and nine source-bound CoMath profile supplements, generated alongside nine portable Codex presets.
- A source-checked configuration renderer for the EXISTING CoMath operator MCP; default read-only tool allowlist, environment-only credential names, no network/process/config mutation.
- Explicit portable versus CoMath-backed skill routing and parity/installation documentation.
- 31 additional conformance tests; selected original-source reproductions, a separate one-line CoMath signature-boundary patch and 13 standalone regression cases.
- Current source-coverage/test/review records; RC1 evidence retained only under docs/v9/archive/rc1.

## Still not provided

Live Codex/CoMath integration, real Lean execution, full Codex/Snow UI lifecycle validation, full original test suites, automatic legacy state migration, installed CoMath prompt supplements, a full replay-chain security audit, or measured mathematical speedup. The legacy JSON context writer remains single-writer only in practice; use v9 or the existing daemon for multiworker research.

---

# 9.0.0-rc1 — 2026-09-27

Independent, additive portable-controller release candidate. Not a full upstream checkout or v8 database migration.

## Added

- Standard-library SQLite/WAL research state, current statement hashes, event history and bounded checkpoints.
- Dependency-aware tasks, attempt budgets, atomic leases, heartbeats, expired-task recovery, descendant invalidation and result/artifact checks.
- Content-addressed evidence with origin freshness, non-destructive withdrawal and adverse-issue resolution.
- Six cumulative gates and snapshot-bound local operator review with explicit trust limitations.
- Explicit constrained Lean replay adapter: version/manifest checks, random exact-type audit theorem, axiom allowlist, current source/toolchain/artifact bindings. Mocked locally; real Lean smoke remains opt-in and was skipped.
- Nine shared role contracts, generated native Codex agent TOML files, draft CoMath adaptations, evidence schemas and unapproved starter templates.
- Nine native Codex command hook handlers with bounded context, checkpoints, limited guardrails and hashed event metadata. No LLM/compile in hooks.
- Non-destructive project installer, idempotent native hook merge, backup/rollback and manifest-bound repository overlay helper.
- Public deterministic conformance tests, elementary research demo, hook-overhead microbenchmark and local-test CI configuration.

## Deliberate changes from the observed old entrypoint

No fixed million-token context target; no infinite stop prevention; no independent-agent fiction; no promotion of experiments or a reviewed informal argument into a Lean certificate. No automatic tool installation, model launch, human self-signoff or legacy-state trust.

## Not included

A verified CoMath daemon adapter, Pi extension changes, authenticated host-only approvals, OS-enforced worker isolation, hermetic transitive-dependency rebuilding, model billing enforcement, novelty guarantees, a measured mathematical productivity gain, or full legacy compatibility.
