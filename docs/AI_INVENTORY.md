# AI supply chain inventory

Handbook §3 Security Requirements → **AI Supply Chain**: *"Track models, datasets, packages, containers and external services"*, evidence: **inventory / provenance**. Submission item 7. §8 Judge check → AI transparency, red flag: **unknown dependencies**.

This file is the **AI** supply chain: which model, which version, which embedding model, which corpus, which external services the AI path touches. It is deliberately separate from two neighbouring documents that are easy to confuse with it:

| Document | Answers |
|---|---|
| **This file** | What models and AI services *the product* depends on at runtime |
| [`AI_USAGE.md`](../AI_USAGE.md) | Which AI tools *the humans* used to write the code (P-06) |
| `trivy` + `make sbom` (CycloneDX artifact) | The **software** supply chain — Python and npm packages |

## Models

### Text generation (converse)

| | |
|---|---|
| Provider | Amazon Bedrock |
| Region | `us-east-1` (`AWS_REGION`, defaults to `us-east-1` in `demo-app/src/demo_app/bedrock.py`) |
| Permitted model ids | `anthropic.claude-3-5-sonnet-20241022-v2:0`<br/>`amazon.nova-lite-v1:0` |
| Where pinned | `bedrock_model_ids` in `infra/variables.tf` (default) and `infra/envs/{dev,prod}.tfvars` |
| Runtime selection | `BEDROCK_MODEL_ID` environment variable. Required unless `TRACEVAULT_FAKE_BEDROCK=1`; the code raises rather than silently picking a default. |
| API | `bedrock-runtime` `Converse` |
| Authorisation | IAM `bedrock:InvokeModel` + `bedrock:InvokeModelWithResponseStream`, scoped to exactly these model ARNs plus the matching inference-profile ARNs. Never `*`. See `infra/oidc.tf` → `BedrockInvokeScoped`, built from `local.bedrock_model_arns` in `infra/main.tf`. |
| Version pinning | Both ids carry explicit versions (`-v2:0`, `-v1:0`). Neither is an alias or a latest-tag. |

Both ids are permitted simultaneously so the second is a live fallback if the first is unavailable or throttled, without an infrastructure change. Exactly one is used per run, recorded on the `llm` span as `gen_ai.request.model`.

**Key inference settings** — set in `demo-app/src/demo_app/bedrock.py`:

| Setting | Value | Why |
|---|---|---|
| `maxTokens` | 256 | Caps output cost and latency per call |
| `temperature` | 0 | Deterministic answers; a demo that reproduces is worth more than a creative one |
| `retries.max_attempts` | 1 | No retry storm against Bedrock; one attempt, then fail |
| `connect_timeout` | 5 s | Fail fast rather than hanging the flight |
| `read_timeout` | 30 s | Matches the Lambda timeout so nothing outlives its caller |

The system instruction is a single line, corpus-grounding only: the question, then `"Answer from this corpus only:"` followed by the retrieved context. It is in source, not configuration, so it changes only by pull request.

### Embeddings

| | |
|---|---|
| Provider | Amazon Bedrock, same region |
| Model id | **Not pinned.** Supplied at runtime via `BEDROCK_EMBED_MODEL_ID`; required unless `TRACEVAULT_FAKE_BEDROCK=1`. |
| API | `bedrock-runtime` `InvokeModel`, body `{"inputText": ...}`, expecting `{"embedding": [...]}` — the Amazon Titan embeddings request/response shape |
| Used for | Embedding the question and the three corpus documents, then cosine similarity to pick top-2 (`RETRIEVE_TOP_K = 2` in `demo-app/src/demo_app/rag.py`) |

> **Gap found while compiling this inventory.** `bedrock_model_ids` contains only the two **converse** models. The IAM policy that authorises Bedrock is generated from that same list, so **no embedding model is in the allowlist** — a live run with `TRACEVAULT_FAKE_BEDROCK` unset would fail the RAG step with `AccessDeniedException`. The `bedrock:InvokeModel` *action* is granted; the embedding model *resource* is not.
>
> This is precisely the class of defect an inventory exercise is supposed to surface: the embedding model was never named, so it was never authorised. Fix is to pin an id (e.g. `amazon.titan-embed-text-v2:0`) and add it to `bedrock_model_ids` so the policy picks it up. Owner: Trevor. Tracked on issue #43.
>
> It has not been hit yet because every test and every local run so far has used `TRACEVAULT_FAKE_BEDROCK=1`, which bypasses both Bedrock calls.

### Fake mode — disclosed stub

`TRACEVAULT_FAKE_BEDROCK=1` replaces **both** Bedrock calls with deterministic local functions:

- Embeddings → a 64-dimensional sha256-derived bag-of-words vector. No network call.
- Converse → the retrieved context echoed back, prefixed `"From the corpus: "`. Reports 1 input token, 1 output token, `cost_usd` 0.0.

Every test in the repository runs in this mode. Per P-15, if a judge demo runs with this flag set, that is **not** live Bedrock and we say so out loud.

### Models not used

No third-party model API beyond Amazon Bedrock — no OpenAI, no Anthropic direct, no Hugging Face Inference. No model weights vendored into the repository. Nothing self-hosted, nothing fine-tuned, no LoRA or adapter. No model runs in CI. No model is in the request path of the vault: `vault-ingest` and `vault-read` make no model calls at all, so a Bedrock outage cannot affect data already recorded.

## Datasets

### RAG corpus

| | |
|---|---|
| Location | `demo-app/corpus/` — `01-overview.md`, `02-retention.md`, `03-tenancy.md` |
| Provenance | **Written by us for this hackathon.** Not scraped, not licensed, not derived from a third party. Three short markdown files describing TraceVault itself. |
| Sensitivity | None. Public project documentation. No PII, real or synthetic. |
| Size | 3 documents, loaded into memory at start; no vector database |
| Access | Read-only. Path-confined with `is_relative_to(root)`; only `*.md` directly under the corpus directory is loaded. |
| Retention | Committed to git as source. Not user data, so retention policy does not apply. |

### Synthetic PII test data

A fake email and a fake SSN, injected by `scripts/demo_pii_flight.sh` and `demo-app --pii`. These exist to prove redaction works and are generated at run time — they are **not committed** and correspond to no real person. `contracts/fixtures/*.json` contain only the already-masked forms (`[EMAIL]`, `[SSN]`) plus a `prompt_hash`, never raw values.

### Not used

No training data. No fine-tuning data. No evaluation dataset. No user data of any kind — the two Cognito accounts are demo tenants. No dataset is downloaded at build or run time.

## External services

Every external dependency of the AI path:

| Service | Purpose | Data sent | Trust |
|---|---|---|---|
| **Amazon Bedrock** (`bedrock-runtime`, `us-east-1`) | Text generation + embeddings | The question and the retrieved corpus text. Under `--pii`, the synthetic email/SSN reach the model as part of the prompt — deliberately, since that is the flight being recorded. | AWS service in our own account, IAM-scoped to named model ARNs |
| **Amazon Cognito** | Authenticating the two demo users for reads | Username and password at the hosted UI | AWS service, our account |
| **AWS Secrets Manager** | Per-tenant ingest keys | Nothing sent; read at invoke | AWS service, our account, under the stack CMK |
| **AWS S3 / DynamoDB / CloudWatch / KMS** | Storage, telemetry, encryption | Masked spans only | AWS services, our account |

**No non-AWS external service is in the AI path.** No vector database, no third-party observability SaaS, no telemetry export, no webhook, no analytics. Nothing is sent outside the AWS account.

One point worth stating because it looks like a contradiction: the synthetic PII **is** sent to Bedrock. TraceVault's guarantee is about what is *persisted*, not about preventing a prompt from reaching the model that must answer it. The prompt reaches Bedrock; only the masked form and a hash reach the vault. A guarantee that the model never sees the prompt would be a different product.

## Packages relevant to the AI path

Full software inventory is the CycloneDX SBOM from `make sbom`, produced as a CI artifact by `.github/workflows/trivy.yml` and deliberately not committed. The AI-relevant pins:

| Package | Where | Role |
|---|---|---|
| `boto3` / `botocore` | `demo-app`, `vault` (Lambda-provided) | Bedrock, S3, DynamoDB, Secrets Manager clients |
| `presidio-analyzer`, `presidio-anonymizer` | `vault/redact/` — **optional, lazily imported** | Named-entity PII detection *in addition to* the deny-list |

The Presidio dependency is worth being precise about: it is **not installed in CI**, and `vault/redact/` imports it lazily inside a `try`. With Presidio absent, redaction runs deny-list-only and the contracted judge-path guarantees still hold; with it present but failing mid-analysis, redaction **fails closed**. No judged behaviour depends on a third-party ML model being available — a deliberate supply-chain decision, tested by `vault/tests/redact/test_fail_closed.py::test_presidio_failure_mid_analysis_fails_closed`.

Both lockfiles (`sdk/uv.lock`, `demo-app/uv.lock`) are committed for reproducibility.

## Traceability summary

| Question a judge might ask | Answer |
|---|---|
| Which model answered this flight? | `gen_ai.request.model` on the `llm` span, recorded per request |
| Which models *could* have answered it? | The two ids in `infra/envs/*.tfvars` — IAM permits nothing else |
| What version? | Explicit in the id; no aliases or latest-tags |
| Could a model be swapped in at runtime? | No. The IAM allowlist is generated from the Terraform variable, so an unlisted model is denied. |
| Where did the RAG documents come from? | `demo-app/corpus/`, written by this team, in git history |
| Was any real personal data used? | No. Synthetic only, generated at run time, never committed |
| Is anything sent to a third party? | No. AWS services in our own account only |
| What if the model provider is down? | Second permitted model id, or the disclosed fake mode. The vault is unaffected — it makes no model calls. |

**Recorded gaps:** the embedding model is unpinned and unauthorised (above); the live converse path hardcodes `cost_usd = 0.0`, so real spend is not yet computed per span. Both owned by Trevor.
