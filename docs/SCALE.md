# Capacity, abuse limits, and the 10× answer

This is the evidence for handbook §3 **Abuse & Cost** and §5 **Scalability**. These are explicit demo assumptions, not load-test results.

## Capacity assumptions and budget

| Item | Demo assumption / control |
|---|---|
| Expected traffic | 10 completed flights/minute; four spans per flight |
| 10× scenario | 100 flights/minute and 400 spans/minute |
| Span/flight size | Assume ≤16 KiB per span and ≤64 KiB per four-span flight; schema validation and masked 200-character previews keep prompts out, but this size is an operating assumption, not a request-size enforcement claim |
| AI work per flight | Three corpus embeddings + one query embedding + exactly one Converse call; no autonomous loop |
| Per-flight AI budget | One agent iteration, 256 generated tokens, 5 s connect timeout, 30 s read timeout, one retry attempt |
| Cost budget | Target **< $0.01 per demo flight** at the bounded workload above. This is a budget ceiling, not a measured pricing claim; the live `cost_usd` estimator is still a disclosed gap and must not be presented as real billing evidence while it emits zero |
| API abuse cap | 10 requests/s steady, burst 20 in dev (`api_throttle_*`) |
| Compute cap | Both Lambdas: 30 s and 512 MiB. The live account's observed regional concurrency quota is 10 shared executions (2026-08-22); `lambda_reserved_concurrency = -1` uses that unreserved pool until AWS approves a higher quota |
| Storage | DynamoDB on-demand; S3 managed scaling; seven-day DynamoDB TTL |

## What breaks first at 10×

The first constraints are **Bedrock request quota/latency and the account's Lambda concurrency quota**, not DynamoDB or S3. At the expected 10 flights/minute and a conservative 2-second average Lambda duration, required concurrency is below one on average. At 100 flights/minute it is about four (`rate × duration` rounded up), within the observed shared account quota of 10 before simultaneous reads are counted. A sustained 30-second worst case would require 50 and is intentionally throttled rather than allowed to run away.

The 10× response is configuration and quota management, not a new architecture:

1. Confirm Bedrock quota and request an increase before raising ingress.
2. Request a Lambda regional-concurrency increase above the current 10. Only after approval, set a positive `lambda_reserved_concurrency` in reviewed environment tfvars so ingest and read cannot starve each other.
3. Raise `api_throttle_rate` and `api_throttle_burst` no higher than the tested downstream capacity.
4. Load-test redaction and ingest with synthetic data, then watch Lambda throttles/duration, API 4xx/5xx, and Bedrock throttles.
5. Keep DynamoDB `PAY_PER_REQUEST` and S3; do not add EKS, OpenSearch, or another queue for this demonstrated load.

The avoidable inefficiency is that the three static corpus documents are re-embedded per demo flight. If Bedrock becomes the first bottleneck, cache those fixed embeddings before changing storage architecture.

## Limit behavior

- **API rate/burst exceeded:** API Gateway returns HTTP **429 Too Many Requests**. The request is not queued and no partial flight is promised; clients back off with jitter and retry within their own bounded policy.
- **Lambda concurrency exhausted:** Lambda invocation is throttled; through API Gateway this is surfaced as an error and contributes to operational signals. Today both functions share the account's unreserved pool of 10. A positive per-function reservation is allowed only after AWS raises the regional quota and requires a reviewed tfvars change.
- **Lambda/API timeout:** API integration is capped at 30 seconds and the Lambda is terminated at 30 seconds. No unbounded worker remains.
- **Bedrock timeout or throttle:** the demo call fails and the span records failure; model output never triggers a write/delete action. Retries are capped at one attempt.
- **Token ceiling reached:** Bedrock stops generation at 256 output tokens; there is no second agent turn.

## Automated evidence

- `demo-app/tests/test_agent_controls.py` proves one tool, path confinement, no side-effect capability reached, one Converse call, token ceiling, and client timeouts.
- `infra/tests/test_capacity_controls.py` pins API throttles, Lambda timeout/memory/concurrency, and agent budget constants to these documented values.
- CI runs both suites through `sdk.yml` and `infra.yml`.
