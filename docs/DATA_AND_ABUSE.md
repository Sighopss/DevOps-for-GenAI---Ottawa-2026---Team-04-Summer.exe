# Data sensitivity and abuse cases

Submission item for the Discover gate (handbook §2 — *what data do we hold, and what did we design against?*). Rubric: Problem & Impact, Security. Issue #39.

Companion documents: [ARCHITECTURE.md](ARCHITECTURE.md) (trust boundaries), root `SECURITY.md` (threat model), root `GOVERNANCE.md` (oversight). This file classifies the data TraceVault handles and walks the six abuse cases the vault was designed against, each mapped to the test or control that covers it — or explicitly marked as accepted risk.

## Data classification

TraceVault is an observability store for AI requests. The core design constraint (PLAN.md): **observability must not become a data-leakage mechanism.** The classification below is enforced by code, not by policy: the span schema (`contracts/span.schema.json`) has `additionalProperties: false` and ingest rejects unknown fields, so there is no field in which unclassified data can arrive.

| Class | Fields | Handling |
|---|---|---|
| **Never stored, never logged** | Raw prompts; `X-Tenant-Key` values; Cognito tokens/claims | The schema has no raw-prompt field; unknown span fields are rejected at ingest (`vault/ingest/validate.py`). Handlers never log headers, bodies, or claims. |
| **Sensitive-derived, stored masked only** | `prompt_preview`, `name`, `error_message`, every string inside `attributes` / `events` | Re-masked at ingest by `vault/redact` regardless of what the SDK already did (deny-list: email, SSN in three formats, AWS `AKIA`/`ASIA` keys, `sk-` secrets; Presidio best-effort on top). Any unmaskable value fails the whole batch closed — 400 `redaction_failed`, nothing stored. |
| **Non-reversible derivative** | `prompt_hash` | SHA-256 of the original prompt. Identifies a payload for audit without containing it. |
| **Operational, non-sensitive** | `trace_id`, `span_id`, `parent_id`, `tenant_id`, `kind`, `status`, timestamps, `gen_ai.request.model`, token counts, `cost_usd` | Schema-typed and validated; persisted unchanged. |
| **Audit records** | `actor`, `tenant_id`, `trace_id`, `ts` | Exactly four fields (`vault/audit/models.py`) — an audit row cannot leak prompt data because it never holds any. |

**Synthetic demo PII.** Every SSN/email in fixtures, tests, and `scripts/demo_pii_flight.sh` is fabricated (e.g. `123-45-6789`, `user@example.com`). No real personal data enters the system at any point in the demo.

**Retention.** DynamoDB TTL 7 days (`expires_at`, on both flight summaries and audit rows). CloudWatch logs 7 days. S3 span payloads become unreachable when their DynamoDB item expires (reads resolve through the item); the objects themselves have no lifecycle rule yet — see accepted risks.

**Redaction engine — decision (issue #84).** The deny-list is the **authoritative** layer: deterministic regex, stdlib-only, shipped in the Lambda, proven against the live store (nothing raw at rest — see `docs/RED_TEAM.md`). Presidio (ML named-entity detection) is a *best-effort* second pass that is **declared absent in production** — it is not installed in CI and not packaged in the Lambda zip; `vault/redact/` imports it lazily inside a `try`, so with it absent redaction runs deny-list-only and every contracted judge-path guarantee still holds, and with it present-but-failing it fails closed (`vault/tests/redact/test_fail_closed.py`). We do **not** claim Presidio is active: no judged behaviour depends on a third-party ML model being available. Full dependency note: `docs/AI_INVENTORY.md`.

## Abuse cases

Each case names the control **and** the test a judge can run (`python -m pytest vault`).

### 1. Cross-tenant read

*A tenant-b user requests a tenant-a `trace_id`.*

Control: every read is scoped to the JWT's `custom:tenant_id`; a foreign trace returns **403 with the contract body, never 404**, and lists never include foreign flights. A Cognito *access* token (which passes the gateway authorizer but carries no tenant claim) fails closed as 401.

Tests: `vault/tests/read/test_isolation.py` — `test_cross_tenant_read_is_403_not_404_exact_fixture_body`, `test_tenant_b_list_never_shows_tenant_a`, `test_missing_tenant_claim_401_fail_closed`.

### 2. PII exfiltration via prompt

*A prompt containing an email + SSN is sent through the demo flight; the attacker hopes the store keeps it.*

Control: authoritative re-redaction at ingest over **every** free-text field, including nested `attributes`/`events` values; deny-list covers formatted, spaced, bare-nine-digit SSNs, emails (unicode local parts included), AWS keys mid-token, `sk-` secrets. Unmaskable ⇒ fail closed, nothing stored.

Tests: `vault/tests/ingest/test_pipeline.py::test_pii_in_any_text_field_never_reaches_rest`, `vault/tests/redact/test_boundary_bypass.py` (every bypass from issue #45), `test_fail_closed.py`.

### 3. Prompt injection through ingested span text

*A span carries "ignore previous instructions…" hoping something downstream executes it.*

Control: span text is inert data end-to-end — the vault never feeds stored text to an LLM or shell; it is masked, stored, and rendered. The Explorer renders it as text (Michael's `web/` lane owns the on-screen half — issue #62).

Tests: `vault/tests/ingest/test_adversarial.py::test_prompt_injection_stored_as_inert_data`.

### 4. Runaway agent loop / token burn

*A looping agent (or a hostile client) floods ingest with spans.*

Controls in the vault: ≤100 spans per batch, one `trace_id` per batch, 1 MB body cap, 10k-char per-field cap (also the ReDoS gate), depth-32 attribute nesting cap — each violation is a contract 4xx, nothing stored. Platform half (Trevor): WAF managed rules and the 5xx alarm; DynamoDB is on-demand billing with 7-day TTL, so flood damage is bounded in time.

Tests: `vault/tests/ingest/test_validate.py::test_oversize_batch_rejected`, `test_adversarial.py` (body/nesting/length caps).

**Accepted risk:** no per-tenant rate limit on ingest. At demo scale, API Gateway default throttling + WAF + the batch caps bound the blast radius; a production deployment would add usage plans / per-key throttling.

### 5. Stolen ingest key

*An attacker obtains a tenant's `X-Tenant-Key`.*

Controls: the key is write-only — it cannot read anything (reads require a Cognito ID token). A key can only write into **its own** tenant: `span.tenant_id` must match the key's tenant or the batch is rejected, so a stolen tenant-a key cannot pollute tenant-b. Keys live in Secrets Manager (values never in git — gitleaks runs on every PR) and rotate with one `put-secret-value` (`infra/README.md`); ingest re-reads on cold start. Unreadable or placeholder secrets authenticate nobody.

Tests: `vault/tests/ingest/test_tenant_key.py`, `test_validate.py::test_span_tenant_must_match_key_tenant`.

**Accepted risk:** until rotation, the thief can write garbage flights into the *stolen key's own tenant* (integrity, not confidentiality). TTL expires the pollution in 7 days.

### 6. Log scraping

*An attacker with CloudWatch access hunts for PII in logs.*

Control: handlers never log request bodies, headers, or claims; validation errors name fields, never values; redaction errors carry entity type names only; unexpected exceptions return a fixed body (`internal error`) rather than `str(exc)`, which could echo payload fragments.

Tests: `vault/tests/redact/test_no_raw_leak.py`, `vault/tests/ingest/test_handler.py::test_handler_never_writes_pii_to_stdout_or_logs`, `test_validate.py::test_error_messages_never_contain_values`, `test_handler.py::test_store_failure_500_fixed_body_no_leak`.

**Live half (issue #53/#18):** after deploy, the same assertions run against real CloudWatch log groups and S3 — a demo flight with PII in the prompt, then grep the logs and the bucket.

## Accepted risks (summary)

| Risk | Why accepted for the 48h | Production path |
|---|---|---|
| No per-tenant ingest rate limit | WAF + gateway throttling + batch caps bound it at demo scale | API keys with usage plans |
| S3 payload objects have no lifecycle rule | Objects are unreachable once the Dynamo item's TTL expires; bucket is SSE-KMS, private, tenant-prefixed IAM | S3 lifecycle expiry matching the TTL |
| Stolen key can pollute its own tenant until rotated | Write-only key, cross-tenant write impossible, 7-day TTL | Shorter-lived keys, anomaly alarms |
