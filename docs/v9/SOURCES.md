# Source index — RC2

Reviewed 2026-09-27, Australia/Brisbane. Source-backed observations, local reproductions and proposed architecture changes are distinct. No full-clone, full-paper or full-proof audit is implied.

## Pinned repository sources

### C01 — `CONTRIBUTING.md`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/CONTRIBUTING.md

Scope: complete text.

### C02 — `docs/architecture/durable-research-orchestration.md`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/docs/architecture/durable-research-orchestration.md

Scope: complete text.

### C03 — `services/comathd/src/agents/agent-profiles.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/agent-profiles.ts

Scope: profile declarations and selected launch/validation code; not complete file audit. Git blob: `8dab66d0f0186168d4344e3d07b4a1460cd9acb6`.

### C04 — `services/comathd/src/agents/role-templates.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/role-templates.ts

Scope: complete text.

### C05 — `services/comathd/src/research/context-pack-builder.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/research/context-pack-builder.ts

Scope: complete text.

### C06 — `services/comathd/src/research/context-service.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/research/context-service.ts

Scope: complete text in two ranges. Git blob: `02b63eacf8437a3a129a4975978aeff67a6d964e`.

### C07 — `services/comathd/src/agents/runtime/worker-execution-host.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/runtime/worker-execution-host.ts

Scope: selected leading lifecycle/dispatch/event/accounting code; final response truncated.

### C08 — `services/comathd/src/agents/runtime/codex-app-server-adapter.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/runtime/codex-app-server-adapter.ts

Scope: lines 1-140; rest not read. Git blob: `1f24a1fa7c3e64ef4c517e95a11a19ed990183be`.

### C09 — `services/comathd/src/control/research-mcp-facade.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/control/research-mcp-facade.ts

Scope: complete text across overlapping ranges. Git blob: `e9d9a9e54b6b87f272715c4614635d438e904774`.

### C10 — `services/comathd/src/proof-kernel/lean/statement-signature.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/proof-kernel/lean/statement-signature.ts

Scope: complete text; exact Git blob materialized; original and patched standalone execution. Git blob: `7d5dab316a75180649016872f724a6718e618e70`.

### C11 — `services/comathd/src/proof-kernel/lean/statement-equivalence.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/proof-kernel/lean/statement-equivalence.ts

Scope: lines 1-170 plus symbol-reference search; not complete checker. Git blob: `ea6de954ec37917e3e27d2b83b70e5f35c4e90f5`.

### C12 — `services/comathd/src/proof-kernel/lean/statement-diff-gate.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/proof-kernel/lean/statement-diff-gate.ts

Scope: complete text; not integration-tested.

### C13 — `services/comathd/src/proof-kernel/ensemble/service-owned-lean-evidence.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/proof-kernel/ensemble/service-owned-lean-evidence.ts

Scope: lines 1-150; downstream verifier dependencies not fully read. Git blob: `99149d06ad1c6f1a4f405ee18cf7f1baebcf710f`.

### C14 — `.pi/agents/formalization.md`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/.pi/agents/formalization.md

Scope: complete text. Git blob: `4c9e6ae1383cd0fb13fc95adf4d258e1e6e92bba`.

### C15 — `services/comathd/package.json`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/package.json

Scope: complete text. Git blob: `60eab14efbecbac514f9a9e8fbbf853b515b855d`.

### C16 — `services/comathd/tsconfig.json`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/tsconfig.json

Scope: complete text. Git blob: `8a2969c8591b6d2d21b65b61e4bfb21798c2fd36`.

### C17 — `services/comathd/src/agents/agent-run-scheduler.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/agent-run-scheduler.ts

Scope: selected leading scheduling code (request lines 1-240); not full scheduler audit.

### C18 — `services/comathd/src/agents/runtime/codex-api-adapter.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/agents/runtime/codex-api-adapter.ts

Scope: complete text; retries not run. Git blob: `6a5779c799057bb62f98272a9b6786d32d005eb0`.

### C19 — `services/comathd/src/errors.ts`

https://github.com/DerstedtCasper/comath-pi-lab/blob/e8e0182823b383cb228802c4d70f3309bf0a698c/services/comathd/src/errors.ts

Scope: complete text. Git blob: `129b1c8ec306f3967b79baec323081d7727b4390`.

### M01 — `skill/runtime/proof_factory_v8.py`

https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/skill/runtime/proof_factory_v8.py

Scope: complete text; exact Git blob materialized; original function reproductions and patched tests. Git blob: `6f362d40efd0cd2a183f2ceb70889b84d46f7f97`.

### M02 — `skill/runtime/moe_router_v8.py`

https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/skill/runtime/moe_router_v8.py

Scope: complete text; exact Git blob materialized. Git blob: `ce5444abc91f185cba5a000291fc7c61dc0abb6f`.

### M03 — `tests/test_proof_factory_v8.py`

https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/tests/test_proof_factory_v8.py

Scope: complete text; exact Git blob materialized; all 4 selected tests run. Git blob: `b90d2413997c331d539ce95b7dafa929dce2f9b1`.

### M04 — `skill/scripts/proof_factory_v8.py`

https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/skill/scripts/proof_factory_v8.py

Scope: complete CLI wrapper text. Git blob: `be5a5eca6f4ed2528add5e88f29f4b2155e42b48`.

### M05 — `skill/scripts/final_audit.py`

https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/skill/scripts/final_audit.py

Scope: lines 1-150; rest and full release call graph not read. Git blob: `5657aa645cbd1082bbd46a87cbec7c104cff646b`.

### M06 — `LICENSE`

https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/LICENSE

Scope: complete text. Git blob: `d6e2db300e1284e9bd658cc166f09ecd08ffda21`.

### M07 — `MATHPROVE_V7_PATCH_NOTES.md`

https://github.com/DerstedtCasper/MathProve-Skill/blob/e4aaf6abec8c05bc5186d635b06b56152442380b/MATHPROVE_V7_PATCH_NOTES.md

Scope: complete text. Git blob: `d84b336ff2180371342139770abeb2803c643c20`.

## Primary engineering / research sources

### W01 — Codex hooks

https://developers.openai.com/codex/hooks

Scope: Current official documentation; event/context configuration checked, no live host.

### W02 — Codex MCP

https://developers.openai.com/codex/mcp

Scope: Current official config fields; rendered TOML tested locally, no live MCP.

### W03 — Codex subagents

https://developers.openai.com/codex/subagents

Scope: Current official custom agent configuration documentation.

### W04 — OpenAI — Early experiments in accelerating science with GPT-5 (2025-11-20)

https://openai.com/index/accelerating-science-gpt-5/

Scope: Official article, not full paper or independent proof replay.

### W05 — Anthropic — How we built our multi-agent research system (2025-06-13)

https://www.anthropic.com/engineering/multi-agent-research-system

Scope: Official engineering article; not a mathematical task benchmark.

### W06 — Anthropic — Effective harnesses for long-running agents (2025-11-26)

https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents

Scope: Official coding-agent engineering article; transfer to mathematics is a design proposal.

### W07 — Towards Autonomous Mathematics Research, arXiv:2602.10177

https://arxiv.org/abs/2602.10177

Scope: Primary abstract/version metadata, v3 2026-03-06; full PDF not analyzed.

## Historical material

RC1 sources and microbenchmarks are retained under archive/rc1. They must not be presented as newly run RC2 or CoMath measurements. The CI workflow is inherited; remote Actions execution and the complete upstream test matrix were not run in this audit.
