"""Stdlib validation of the ingest batch against contracts/span.schema.json.

No jsonschema dependency (CI and the Lambda zip stay stdlib-only), so the
locked schema's contractual essentials are enforced by hand. Fail-closed
posture: unknown span keys are rejected (`additionalProperties: false`) —
an unexpected field is a place raw PII could hide from redaction.

Raises InvalidBatch; callers map it to 400 `invalid`. Exception messages
name fields, never values.
"""

from __future__ import annotations

import re

MAX_SPANS_PER_BATCH = 100

_TENANTS = {"tenant-a", "tenant-b"}
_KINDS = {"llm", "tool", "rag", "http"}
_STATUSES = {"ok", "error"}
_HASH_RE = re.compile(r"^[a-f0-9]{64}$")

_REQUIRED: dict[str, type] = {
    "trace_id": str,
    "span_id": str,
    "tenant_id": str,
    "kind": str,
    "name": str,
    "status": str,
    "start_time": str,
    "end_time": str,
}

_OPTIONAL: dict[str, tuple] = {
    "parent_id": (str, type(None)),
    "gen_ai.request.model": (str,),
    "gen_ai.usage.input_tokens": (int,),
    "gen_ai.usage.output_tokens": (int,),
    "cost_usd": (int, float),
    "error_message": (str, type(None)),
    "attributes": (dict,),
    "events": (list,),
    "prompt_preview": (str,),
    "prompt_hash": (str,),
}


class InvalidBatch(Exception):
    """Batch violates the span contract. Message carries field names only."""


def _fail(reason: str):
    raise InvalidBatch(reason)


def _check_span(span: object, index: int) -> None:
    if not isinstance(span, dict):
        _fail(f"spans[{index}] is not an object")

    unknown = set(span) - set(_REQUIRED) - set(_OPTIONAL)
    if unknown:
        _fail(f"spans[{index}] has unknown fields: {sorted(unknown)}")

    for field_name, expected in _REQUIRED.items():
        if field_name not in span:
            _fail(f"spans[{index}] missing {field_name}")
        if not isinstance(span[field_name], expected):
            _fail(f"spans[{index}].{field_name} has wrong type")

    for field_name, expected in _OPTIONAL.items():
        if field_name in span and not isinstance(span[field_name], expected):
            _fail(f"spans[{index}].{field_name} has wrong type")
        # bool is an int subclass; token counts must be true integers
        if field_name in span and expected == (int,) and isinstance(span[field_name], bool):
            _fail(f"spans[{index}].{field_name} has wrong type")

    if not 16 <= len(span["trace_id"]) <= 64:
        _fail(f"spans[{index}].trace_id length out of range")
    if not 8 <= len(span["span_id"]) <= 32:
        _fail(f"spans[{index}].span_id length out of range")
    if span["tenant_id"] not in _TENANTS:
        _fail(f"spans[{index}].tenant_id not a known tenant")
    if span["kind"] not in _KINDS:
        _fail(f"spans[{index}].kind not in llm|tool|rag|http")
    if span["status"] not in _STATUSES:
        _fail(f"spans[{index}].status not in ok|error")
    if not 1 <= len(span["name"]) <= 128:
        _fail(f"spans[{index}].name length out of range")
    if "prompt_hash" in span and not _HASH_RE.match(span["prompt_hash"]):
        _fail(f"spans[{index}].prompt_hash is not 64 lowercase hex")
    if "prompt_preview" in span and len(span["prompt_preview"]) > 200:
        _fail(f"spans[{index}].prompt_preview exceeds 200 chars")
    if "cost_usd" in span and span["cost_usd"] < 0:
        _fail(f"spans[{index}].cost_usd negative")
    for token_field in ("gen_ai.usage.input_tokens", "gen_ai.usage.output_tokens"):
        if token_field in span and span[token_field] < 0:
            _fail(f"spans[{index}].{token_field} negative")


def validate_batch(body: object, tenant_id: str) -> list[dict]:
    """Validate `{"spans": [...]}` for the authenticated tenant.

    Every span must carry the key's tenant_id (a tenant key must not write
    under another tenant) and one batch is one flight (single trace_id)."""
    if not isinstance(body, dict) or not isinstance(body.get("spans"), list):
        _fail("body must be an object with a spans array")
    spans = body["spans"]
    if not spans:
        _fail("spans is empty")
    if len(spans) > MAX_SPANS_PER_BATCH:
        _fail("too many spans in one batch")

    for i, span in enumerate(spans):
        _check_span(span, i)
        if span["tenant_id"] != tenant_id:
            _fail(f"spans[{i}].tenant_id does not match the presented key")

    trace_ids = {span["trace_id"] for span in spans}
    if len(trace_ids) != 1:
        _fail("one batch must contain exactly one trace_id")

    return spans
