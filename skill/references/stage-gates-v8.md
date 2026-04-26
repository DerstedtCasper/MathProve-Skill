# Stage Gates v8

Use stage gates to prevent proof-search drift. Every stage has: entry artifacts, minimum work quota, accepted outputs, hard vetoes, and rewind rule.

## 0. Problem lock

Entry: user problem or document. Outputs: `problem_lock.md`, theorem variants, assumptions ledger. Minimum: identify variables, domain, target formal system, and at least one false/ambiguous reading. Veto: ambiguous goal, missing domain, impossible route not marked as conjectural. Rewind: ask for or infer a narrower theorem variant and record the choice.

## 1. Knowledge pack

Entry: problem lock. Outputs: `knowledge_pack.md`, `library_search.jsonl`, citations, prior memory hits. Minimum: search local docs/Mathlib memory before inventing lemmas. Veto: using unverified lemma names as facts, missing import rationale. Rewind: split into local lemma search tasks.

## 2. Notation/definition

Entry: problem lock + knowledge pack. Outputs: `notation_ledger.md`, `namespace_plan.md`, theorem signature draft. Minimum: resolve overloaded symbols, coercions, index origin, exact equality/equivalence direction. Veto: undefined symbol, domain drift, hidden nonzero/positivity assumptions. Rewind: strengthen or weaken theorem signature.

## 3. Skeleton

Entry: definitions + theorem signature. Outputs: `Skeleton.lean`, `lemma_dag.json`, `skeleton_report.md`. Minimum: top theorem plus leaf lemmas with dependency edges. `sorry` allowed only here. Veto: cyclic DAG, theorem drift, unmotivated giant lemma, missing import. Rewind: split lemma or alter namespace/import plan.

## 4. Line map

Entry: skeleton and informal proof. Outputs: `line_map.json`, obligation table. Minimum: each informal line maps to a formal target or explicit gap. Veto: hidden many-to-one leap, unmapped line, self-dependency, false converse. Rewind: add intermediate lemma or mark unsupported line.

## 5. Lemma sprint

Entry: leaf obligations. Outputs: candidate packs, Lean logs, proof patches. Minimum: run parallel attempts or create task cards for unavailable workers; record failures. Veto: non-skeleton `sorry`, Lean error, missing log, stale candidate, new axiom, failed dependency. Rewind: extract smaller lemma, change rewrite direction, add local simp lemma, or update statement.

## 6. Refutation/red team

Entry: verified/proposed lemmas. Outputs: `red_team_report.md`, counterexample log, hazard ledger. Minimum: test quantifier boundaries, small finite models when applicable, degenerate cases, converse directions, and typeclass assumptions. Veto: unresolved counterexample, theorem weakening not recorded, edge case ignored. Rewind: repair theorem or create failure certificate.

## 7. Integration/refactor

Entry: accepted lemma patches and red-team result. Outputs: `Integrated.lean`, import profile, refactor report. Minimum: replay merged file, remove duplicated lemmas, check namespace hygiene. Veto: non-replayable patch, excessive hidden dependencies, broken import, style that blocks maintainability. Rewind: isolate conflicting patches or replay smaller bundle.

## 8. Final audit

Entry: integrated proof. Outputs: `audit.json`, `Solution.md`. Minimum: static forbidden-token scan, Lean replay, dependency/axiom profile, evidence coverage map. Veto: `sorry`, `admit`, `unsafe`, `axiom`, failed replay, missing evidence link. Rewind: return to integration or lemma sprint.

## 9. Memory update

Entry: final result or failure certificate. Outputs: proof-memory events. Minimum: store theorem statement, proof route, imports, failures, reusable repair patterns, and counterexamples. Veto: append-only dump without relation labels. Rewind: compress events and add stable IDs.
