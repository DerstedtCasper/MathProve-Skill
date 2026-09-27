# Reproduction scope

`mathprove_v8_observations.py` requires an ORIGINAL file with Git blob 6f362d40efd0cd2a183f2ceb70889b84d46f7f97. It intentionally refuses the patched RC2 file. Run it against a separate original checkout; it performs no Lean/network calls and only uses temporary files. The controlled two-writer test forces both reads before either write; it is a deterministic lost-update interleaving, not a random throughput benchmark.

`mathprove-v8-observed.json` and `comath-signature-observed.json` describe original-source behavior. The score reproducer is not a demonstrated final_audit.py or kernel bypass. `comath-signature-patched.json` records 13 standalone patched TypeScript-module cases; no real Lean process or complete CoMath build ran.

The CoMath regression script is one directory up. After compiling the reviewed module, run `node review/comath-signature-regression.cjs PATH_TO_COMPILED_JS`. Against the original parser it reports failed expectations; against the supplied patch all 13 cases pass.
