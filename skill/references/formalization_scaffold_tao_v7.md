# Tao-style formalization scaffold

Use this when translating an informal proof into Lean.

## Step 0: Formalize objects and notation

Create the Lean namespaces, variables, structures, and notation.  Do not prove the theorem yet.

## Step 1: Build the skeleton

Write lemma/theorem statements with dependency comments.  `sorry` is allowed only here, so that Lean can check statement shapes and dependencies.

## Step 2A: Line map

Translate each informal proof line into an atomic obligation.  Each line must list:

- informal source line;
- formal target declaration;
- dependencies;
- expected tactic family;
- risk notes.

## Step 2B: Lemma sprint

Fill one lemma at a time.  Use local isolated branches.  Promote only candidates with compiler logs.

## Step 3: Integration/refactor

Merge proof patches, minimize imports, stabilize names, and remove `sorry`.

## Step 4: Final audit

Run static forbidden-token scan, Lean replay, and axiom printing.  No final claim is allowed before this gate.
