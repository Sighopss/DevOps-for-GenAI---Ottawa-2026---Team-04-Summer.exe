"""Record and list audit events.

Item shape (traces table, PK tenant_id, SK from vault/store/keys.py):
    SK = a#{trace_id}#{ts}#{entropy}   (entropy keeps same-microsecond
                                        events from overwriting each other)
    attrs: actor, tenant_id, trace_id (bare), ts, expires_at (same TTL
    policy as span data — audit history also expires, PLAN.md).

Query uses string KeyConditionExpressions so nothing here imports boto3;
tests inject a fake table, Lambda wiring passes a real Table resource.
This package never parses JWTs — the read handler passes `actor` in.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone

from vault.audit.models import AuditEvent
from vault.store import keys

_DEFAULT_TTL_DAYS = 7


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _ttl_epoch() -> int:
    days = int(os.environ.get("VAULT_TTL_DAYS", _DEFAULT_TTL_DAYS))
    return int(time.time() + days * 86400)


def _table_or_default(table):
    if table is not None:
        return table
    import boto3  # Lambda runtime provides it; tests always inject

    return boto3.resource("dynamodb").Table(os.environ["TABLE"])


def record(actor: str, tenant_id: str, trace_id: str, table=None) -> AuditEvent:
    """Write one audit row. Returns the recorded event."""
    event = AuditEvent(
        actor=actor, tenant_id=tenant_id, trace_id=trace_id, ts=_now_iso()
    )
    sort_key = keys.audit_sk(trace_id, f"{event.ts}#{uuid.uuid4().hex[:8]}")
    _table_or_default(table).put_item(
        Item={
            "tenant_id": tenant_id,
            "trace_id": sort_key,
            "actor": actor,
            "flight_trace_id": trace_id,
            "ts": event.ts,
            "expires_at": _ttl_epoch(),
        }
    )
    return event


def list_events(tenant_id: str, trace_id: str, table=None) -> list[AuditEvent]:
    """Events for exactly one (tenant_id, trace_id), oldest first."""
    response = _table_or_default(table).query(
        KeyConditionExpression="tenant_id = :t AND begins_with(trace_id, :p)",
        ExpressionAttributeValues={
            ":t": tenant_id,
            ":p": keys.audit_sk(trace_id, ""),
        },
    )
    events = [
        AuditEvent(
            actor=str(item["actor"]),
            tenant_id=str(item["tenant_id"]),
            trace_id=str(item["flight_trace_id"]),
            ts=str(item["ts"]),
        )
        for item in response.get("Items", [])
    ]
    return sorted(events, key=lambda event: event.ts)
