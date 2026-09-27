# CoMath-backed mode — existing daemon is the authority

Select this mode only when the user intends to use an existing CoMath deployment and the host exposes its operator MCP. Do not silently fall back to a local database when the service is missing. Report the missing capability and preserve the selected mode. Portable hooks/agents are not required for this mode; avoid installing a second orchestration layer.

Reviewed contract: CoMath `e8e0182823b383cb228802c4d70f3309bf0a698c`. The existing stdio entry is `services/comathd/dist/control/research-mcp-facade.js`, built from `services/comathd/src/control/research-mcp-facade.ts`. The repository-level helper `scripts/comath_codex_config.py` prints a source-pinned configuration; it is not installed as a skill command and does not deploy the service. The MCP reads `COMATH_OPERATOR_BASE_URL` and `COMATH_OPERATOR_TOKEN` from its environment. Never put secret values in prompts, committed config, or task artifacts.

Start with `research_capabilities_get`; inspect campaign list/current state and ask for a definite campaign selection only when it remains genuinely ambiguous. Read the actual frontier, task/checkpoint, budget and events. The read-only generated tool allowlist cannot start or change work. Operator access must be explicitly chosen by the user; a service mutation still goes through the original authorization and revision checks.

For mutations use fresh command IDs and the current expected/base revision supplied by the service. On timeout or uncertain response, query operation/campaign state before retrying; do not create duplicate tasks or campaigns speculatively. Distinguish operator permission to request intake review from host authority to approve it. Never request host-ticket issuance or substitute a worker lease for an operator token.

No `mathprove.py init/start/review` or `.mathprove` shadow ledger for the same campaign. No portable lease token, `reviewed_formal_local` status, or `mp_*` task-result JSON imported as a CoMath result. The original daemon remains responsible for tasks, evidence, accepted results and final proof status. A read result can be summarized for the user but cannot be promoted to a formal certificate by the assistant.

Use only the actual tool IDs and wire schemas. Child-agent reports, durable research_result, checkpoint and formal_candidate are different contracts. Profile supplements in `integrations/comath/profiles/` are repository review materials, not auto-loaded worker prompts; deployment must connect reviewed, versioned instruction artifacts to the actual service context policy.

If shared/local notes are needed, label them advisory and keep service IDs and immutable references. Never mirror a trusted success flag into an independent authoritative store. Server completion, candidate acceptance, independent mathematical review, Lean replay and novelty are distinct statements.

Acceptance still required: live MCP startup/discovery; read-only policy enforcement; revision conflict/timeout recovery; host approval remains unavailable to the operator; a complete research task/checkpoint round trip; and a reviewed formal target's real replay. These have NOT been run in the delivery environment.
