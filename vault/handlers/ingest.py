"""vault-ingest Lambda: POST /v1/traces (API Gateway HTTP API v2 payload).

Never logs headers or the request body — the payload may contain PII until
redaction has run, and the header carries the tenant key.
"""

from __future__ import annotations

import base64
import json

from vault import errors
from vault.ingest import pipeline, tenant_key
from vault.store import FlightStore

_store = None

# API Gateway caps payloads well above this; anything near it is hostile.
_MAX_BODY_BYTES = 1_000_000


def _get_store() -> FlightStore:
    global _store
    if _store is None:
        _store = FlightStore()
    return _store


def _parse_body(event: dict):
    raw = event.get("body")
    if raw is None:
        return None
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except Exception:
            return None
    if isinstance(raw, str) and len(raw) > _MAX_BODY_BYTES:
        return None
    try:
        # RecursionError: a nesting bomb must be a 400, not an unhandled 500
        # (issue #46).
        return json.loads(raw)
    except (TypeError, ValueError, RecursionError):
        return None


def handler(event: dict, context=None, store=None, fetch=None) -> dict:
    """`store` and `fetch` exist for tests; Lambda calls (event, context)."""
    try:
        tenant_id = tenant_key.resolve(event.get("headers") or {}, fetch=fetch)
        if tenant_id is None:
            return errors.error_response("unauthorized")

        body = _parse_body(event)
        if body is None:
            return errors.error_response("invalid")

        return pipeline.ingest(tenant_id, body, store or _get_store())
    except Exception:
        # Fixed body; str(exc) could echo payload fragments (PII) or ARNs.
        return errors.error_response("internal")
