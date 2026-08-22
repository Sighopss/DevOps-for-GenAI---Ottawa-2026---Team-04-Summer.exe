# Product
<!-- impeccable:product-schema 1 -->

## Register

product

## Platform

web

## Stack

Next.js 15 App Router, output export, Cognito hosted UI, fixtures then GET /v1/traces*.

## Users

On-call ML/SRE reconstructing one AI request. One welcome gate at `/`, then operate. Not a campaign site.

## Elevator Pitch

TraceVault helps an on-call ML/SRE replay one AI request end to end without turning observability into another leak path. Instead of bouncing between logs, traces, and ad hoc notes, the operator gets one tenant-scoped view for latency, RAG hops, tokens, cost, and redaction state.

## Product Purpose

Replay one request (LLM, tools, RAG, cost, errors) without storing raw prompts or PII.

## Brand Personality

Operational, high-trust, fail-closed. Calm under pressure, precise, and governance-forward.

## Positioning

Write-time redaction, tenant isolation. Not Grafana. Not Langfuse.

## Adoption Argument

The honest number in this build is workflow compression: four operator questions collapse into one screen. What happened, where time went, what the model spent, and whether data was withheld all land in one exported explorer view, while raw prompts never persist and traces expire after seven days.

## Anti-references

Grafana KPI walls. Langfuse-style observability theater. Cream Inter dashboards. Extra marketing routes. Generic metric-card admin UI.

## Design Principles

- Reconstruct one flight fast, without making the operator hunt.
- Show governance as a product property, not a footnote.
- Keep the UI operational and legible under pressure.
- Use visual emphasis to clarify state, not decorate telemetry.
- Prefer one clear path from welcome to trace detail over broad navigation.

## Surfaces

- Welcome at `/`: mark, one-line purpose, sign-in, fixture fallback.
- Signed-in flight list with detail via `?trace_id=` only.
- Waterfall plus RAG hops for one reconstructed flight.
- Audit / tenant strip with `REDACTED`, tenant, TTL, and forbidden read handling.

## Visual Anchors

- Background `#000000`
- Text `#F8F8F8`
- Blue `rgb(0, 8, 248)`
- Cyan `rgb(0, 248, 248)`

## Constraints

Raw prompts never persist. Cross-tenant 403. Every view audited. DynamoDB TTL. TraceVault black/blue/cyan. Unauthenticated `/` is welcome + Sign in only — no extra marketing routes.

## Accessibility & Inclusion

WCAG AA baseline. Reduced-motion support. High-contrast default presentation suitable for operational use. No critical meaning conveyed by color alone.

## Terminology

Flight = one trace. Kinds: llm, tool, rag, http.
