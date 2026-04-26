# Proof Memory Graph v8

Maintain graph memory so campaigns can exceed one context window.

## Event fields

`event_id`, `event_type`, `subject`, `relation`, `payload`, `stage`, `source`, `confidence`, `replaces`, `created_at`.

## Relations

`defines`, `uses`, `proves`, `fails_by`, `repairs`, `generalizes`, `specializes`, `refutes`, `renames`, `supersedes`, `depends_on`.

## Retrieval discipline

Retrieve memory before a gate. Summarize only relevant events in the active context. If an event is superseded, keep it but mark the replacement so future agents do not repeat false routes.
