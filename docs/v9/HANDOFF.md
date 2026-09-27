# RC2 handoff — 2026-09-27 Australia/Brisbane

## Baselines and scope

MathProve `e4aaf6abec8c05bc5186d635b06b56152442380b`; CoMath `e8e0182823b383cb228802c4d70f3309bf0a698c`. Source reads came through GitHub; four exact original files were materialized and Git-blob checked. Full clones, private QA, complete replay dependencies and full history were not obtained. The development Git history in the build environment was a local RC1-to-RC2 comparison, not upstream history; it is excluded from the ZIP. No remote changes were made.

## Completed

Selected v8 helper hardening with regressions; real CoMath profile mappings and generated supplements; common research-method text; source-checked existing-operator MCP configuration rendering; hook context-option correction; source-precondition and Git-dirty protection in the overlay; standalone CoMath signature patch and regression; refreshed documentation and source coverage. See TEST-REPORT.md for executions, not the historical rc1 report.

## Preserve before integration

Keep user local edits, original license and v8 state. The overlay is not three-way merge. Do not run it on an empty directory. The selected v8 source needs its expected blob or the identical patched result; changed upstream needs manual review. Do not commit backup/workspace/private token files. Do not install CoMath profile supplements as portable mp_* roles.

## Remaining release gates

In a complete MathProve checkout, apply the reviewed patch and run all original tests, packaging/install routes and cross-platform checks. In a complete CoMath checkout, review/apply the separate parser patch, run build/typecheck and private/public regressions. Review the full statement-equivalence/replay call chain before drawing a system-level soundness conclusion.

Run a real supported Lean project through the v9 verifier and confirm target type, axiom reporting, imports and dependency receipts. Run actual Codex hooks and MCP lifecycle tests on the installed host version; on Windows verify the encoded argv and paths. Add CoMath prompt supplements to host-owned context policy with provenance, blind visibility and actual result-schema tests. Measure equal-budget mathematical tasks before asserting productivity gains.

## Known limits deliberately left in place

Legacy write_context_shard is still not multiwriter-safe; old FULL_PANEL/frontier budget defaults remain legacy behavior. v8 scores remain caller-supplied ranking, not proof evidence. Portable human-ack and file/SQLite controls are cooperative, not host-only authentication. The MCP helper verifies source bytes and entry existence, not a trusted build chain. The parser patch is lexical and does not parse all Lean syntax or replace elaborated/kernel-level target checks.
