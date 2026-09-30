# CoMath-backed research

Use this mode when the research project already runs CoMath. Discover the service's actual tools with its capability endpoint, and use its existing campaign, task and artifact interfaces. Do not initialize a second portable database for the same work.

The normal operator MCP entry is `services/comathd/dist/control/research-mcp-facade.js`. `scripts/comath_codex_config.py --comath-root <path>` generates configuration when that built entry exists; it does not compare source hashes or demand a historical CoMath commit. Supply `COMATH_OPERATOR_BASE_URL` and `COMATH_OPERATOR_TOKEN` through the host environment, not prompts or committed files.

Profile supplements in `integrations/comath/profiles/` describe mathematical responsibilities. Historical registry examples are reference material, not version pins or a live capability promise. Prefer currently discovered service tools and its actual result schema. Portable `spec_hash` compatibility fields and SQLite statuses do not replace a CoMath task contract.

Use current compatible Lean/mathlib, useful compilation feedback and mathematical review. Do not add source fingerprint checks, pinned cold replay, mandatory approval loops or hash-based research gates to this integration. Preserve the intended theorem, check assumptions and report actual proof evidence. The skill does not change the permissions of the external service.
