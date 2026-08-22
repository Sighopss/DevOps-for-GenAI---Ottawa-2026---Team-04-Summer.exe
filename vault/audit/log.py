"""Record and list audit events.

Item shape (traces table, PK tenant_id, SK from vault/store/keys.py):
    SK = a#{trace_id}#{ts}#{seq}#{entropy}
        ts      the same UTC ISO-8601 value as the `ts` attribute, kept in
                the key so a row is readable straight out of the console
        seq     nanoseconds since epoch, zero-padded, strictly increasing
                within a process — this is what orders two events that land
                inside the same microsecond
        entropy keeps concurrent writers from overwriting each other

`ts` on its own cannot order events. It comes from a microsecond-resolution
wall clock (much coarser on some platforms — Windows repeats a timestamp for
~15ms), so two audit writes in one request routinely share it. `seq` breaks
those ties in write order rather than at random.

attrs: actor, tenant_id, trace_id (bare), ts, expires_at (same TTL
policy as span data — audit history also expires, PLAN.md).

Query uses string KeyConditionExpressions so nothing here imports boto3;
tests inject a fake table, Lambda wiring passes a real Table resource.
This package never parses JWTs — the read handler passes `actor` in.
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import datetime, timezone

from vault.audit.models import AuditEvent
from vault.store import keys

_DEFAULT_TTL_DAYS = 7

# Guards _last_ns. A Lambda invocation is single-threaded, but this module is
# importable from anywhere and an uncontended lock costs nothing.
_seq_lock = threading.Lock()
_last_ns = 0


def _stamp() -> tuple[str, int]:
    """One clock read -> (ISO ts, ns sequence).

    The ns value never repeats and never goes backwards within this process,
    so same-microsecond events still get strictly increasing sort keys.
    Across processes it is plain wall-clock ns, which orders them as well as
    the clock allows.
    """
    global _last_ns
    with _seq_lock:
        ns = time.time_ns()
        if ns <= _last_ns:
            ns = _last_ns + 1
        _last_ns = ns

    seconds, micros = divmod(ns // 1_000, 1_000_000)
    stamp = datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    return f"{stamp}.{micros:06d}Z", ns


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
    ts, seq = _stamp()
    event = AuditEvent(actor=actor, tenant_id=tenant_id, trace_id=trace_id, ts=ts)
    sort_key = keys.audit_sk(trace_id, f"{ts}#{seq:019d}#{uuid.uuid4().hex[:8]}")
    _table_or_default(table).put_item(
        Item={
            "tenant_id": tenant_id,
            "trace_id": sort_key,
            "actor": actor,
            "flight_trace_id": trace_id,
            "ts": ts,
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
    # Order on the sort key, not on `ts`: the key carries the ns sequence, so
    # it is a total order. Sorting by `ts` leaves same-microsecond events in
    # whatever order the query happened to return them.
    items = sorted(response.get("Items", []), key=lambda item: str(item["trace_id"]))
    return [
        AuditEvent(
            actor=str(item["actor"]),
            tenant_id=str(item["tenant_id"]),
            trace_id=str(item["flight_trace_id"]),
            ts=str(item["ts"]),
        )
        for item in items
    ]
