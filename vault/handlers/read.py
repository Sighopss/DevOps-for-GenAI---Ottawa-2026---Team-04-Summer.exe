"""vault-read Lambda: the three GET routes under /v1/traces (HTTP API v2).

Routes (contracts/http.md):
    GET /v1/traces?limit=50          -> {"flights":[...]}
    GET /v1/traces/{trace_id}        -> {"trace_id","tenant_id","expires_at","spans":[...]}
    GET /v1/traces/{trace_id}/audit  -> {"events":[...]}   (also WRITES a row)

Isolation: every response is scoped to the JWT's custom:tenant_id; a
foreign trace is 403 (never 404), an unknown one 404. Missing tenant claim
(access token instead of ID token) is 401 — fail closed. Never logs claims
or payloads.
"""

from __future__ import annotations

import re

from vault import errors
from vault.audit import list_events, record
from vault.read import tenant_guard
from vault.read.store_read import ReadStore, flight_row

_MAX_LIMIT = 50

_DETAIL_RE = re.compile(r"^/v1/traces/(?P<trace_id>[^/]+)(?P<audit>/audit)?$")

_store = None


def _get_store() -> ReadStore:
    global _store
    if _store is None:
        _store = ReadStore()
    return _store


def _parse_limit(event: dict) -> int | None:
    """Contract: limit max 50 (clamped). Unparseable/non-positive -> None (400)."""
    params = event.get("queryStringParameters") or {}
    raw = params.get("limit")
    if raw is None:
        return _MAX_LIMIT
    try:
        limit = int(raw)
    except (TypeError, ValueError):
        return None
    if limit < 1:
        return None
    return min(limit, _MAX_LIMIT)


def _route(event: dict) -> tuple[str, str | None]:
    """('list'|'detail'|'audit'|'unknown', trace_id)."""
    path = event.get("rawPath") or ""
    stage = (event.get("requestContext") or {}).get("stage")
    if stage and stage != "$default" and path.startswith(f"/{stage}/"):
        path = path[len(stage) + 1 :]
    if path.rstrip("/") == "/v1/traces":
        return "list", None
    match = _DETAIL_RE.match(path)
    if not match:
        return "unknown", None
    trace_id = (event.get("pathParameters") or {}).get("trace_id") or match["trace_id"]
    return ("audit" if match["audit"] else "detail"), trace_id


def handler(event: dict, context=None, store: ReadStore | None = None) -> dict:
    try:
        identity = tenant_guard.caller(event)
        if identity is None:
            return errors.error_response("unauthorized")
        tenant_id, actor = identity

        active_store = store or _get_store()
        kind, trace_id = _route(event)

        if kind == "list":
            limit = _parse_limit(event)
            if limit is None:
                return errors.error_response("invalid")
            items = active_store.list_flight_items(tenant_id, limit)
            return errors.json_response(
                200, {"flights": [flight_row(item) for item in items]}
            )

        if kind in ("detail", "audit") and trace_id:
            verdict, item = tenant_guard.locate_flight(
                tenant_id, trace_id, active_store.get_flight_item
            )
            if verdict != "ok":
                return errors.error_response(
                    "forbidden" if verdict == "forbidden" else "not_found"
                )

            if kind == "detail":
                spans = active_store.load_spans(list(item.get("s3_keys", [])))
                return errors.json_response(
                    200,
                    {
                        "trace_id": trace_id,
                        "tenant_id": tenant_id,
                        "expires_at": int(item["expires_at"]),
                        "spans": spans,
                    },
                )

            # audit: viewing the audit trail is itself an audited event —
            # record first, then list (the fresh row is part of the answer).
            record(actor, tenant_id, trace_id, table=active_store.table)
            events = list_events(tenant_id, trace_id, table=active_store.table)
            return errors.json_response(
                200, {"events": [event_.to_dict() for event_ in events]}
            )

        return errors.error_response("not_found")
    except Exception:
        # Fixed body: str(exc) could echo claims, keys, or payload text.
        return errors.error_response("internal")
