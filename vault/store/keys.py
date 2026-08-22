"""Key and item shapes shared by ingest, read, and audit.

S3 layout (contract + IAM prefix policy — keys MUST start with tenant_id/):
    {tenant_id}/{trace_id}/{batch_id}.json

DynamoDB (table: PK tenant_id S, SK trace_id S, TTL attr expires_at):
    flight summary item: SK = "t#{trace_id}"
    audit event item:    SK = "a#{trace_id}#{suffix}"  (suffix: see vault/audit/log.py)
The prefixes let the read path Query flights with begins_with("t#") and a
trace's audit rows with begins_with("a#{trace_id}#") without ever scanning
across tenants.
"""

from __future__ import annotations

from decimal import Decimal

FLIGHT_SK_PREFIX = "t#"
AUDIT_SK_PREFIX = "a#"


def s3_key(tenant_id: str, trace_id: str, batch_id: str) -> str:
    return f"{tenant_id}/{trace_id}/{batch_id}.json"


def flight_sk(trace_id: str) -> str:
    return FLIGHT_SK_PREFIX + trace_id


def audit_sk(trace_id: str, suffix: str) -> str:
    return f"{AUDIT_SK_PREFIX}{trace_id}#{suffix}"


def flight_item(
    tenant_id: str,
    trace_id: str,
    summary: dict,
    s3_keys: list[str],
    span_count: int,
    expires_at: int,
) -> dict:
    """Build the Dynamo flight-summary item. `summary` fields are exactly the
    list-endpoint fields from contracts/http.md; cost goes in as Decimal
    (DynamoDB rejects float)."""
    return {
        "tenant_id": tenant_id,
        "trace_id": flight_sk(trace_id),
        "flight_trace_id": trace_id,
        "start_time": summary["start_time"],
        "end_time": summary["end_time"],
        "cost_usd": Decimal(str(summary["cost_usd"])),
        "status": summary["status"],
        "prompt_preview": summary["prompt_preview"],
        "s3_keys": s3_keys,
        "span_count": span_count,
        "expires_at": expires_at,
    }
