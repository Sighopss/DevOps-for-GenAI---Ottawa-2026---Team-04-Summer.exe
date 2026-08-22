# TraceVault overview

TraceVault is an AI Application Flight Recorder. One request is one flight:
a single `trace_id` with nested spans of kinds `http`, `rag`, `tool`, and `llm`.

Judges reconstruct that request in the Explorer: hops, tokens, and cost.
Grafana is not the product. Raw prompts are never stored.

The demo agent has **one** retrieve tool (`get_doc_metadata`). There are no
write, delete, or shell tools.
