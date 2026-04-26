# Context Lake v7

The context lake extends effective working memory by externalizing durable state to files. Store theorem signatures, notation tables, lemma inventories, failed tactic/error pairs, successful repairs, counterexamples, Mathlib imports, branch decisions, and audit logs. Do not store raw private chain-of-thought; store concise decisions and evidence.

Every branch reads `context_lake/shard_index.jsonl` before acting. Every shard starts with a short summary so future agents can load selectively. A project may accumulate 1M+ or 10M+ tokens across shards while keeping the active packet small.
