"""Ingest pipeline: validate -> redact -> store -> 202.

Redaction here is authoritative — the SDK's masking is a hint we re-do, not
trust (PLAN.md: "Alexis still redacts at ingest"). Every free-text field in
every span goes through vault.redact, including attribute and event values,
so adversarial PII hidden outside prompt_preview still never reaches rest
(issue #18). Any unsafe redaction fails the whole batch closed: 400
`redaction_failed`, store never called.

Identifier/enum/timestamp fields are schema-typed and validated, not
redacted: trace_id, span_id, parent_id, tenant_id, kind, status,
start_time, end_time, gen_ai.request.model, prompt_hash, token counts,
cost_usd. Trevor's cost_usd and token counts are persisted unchanged.
"""

from __future__ import annotations

import os
import time

from vault import errors
from vault.ingest import validate
from vault.redact import RedactionError, redact

_DEFAULT_TTL_DAYS = 7

# Free-text span fields masked in place (str values only; None passes).
_TEXT_FIELDS = ("name", "error_message", "prompt_preview")


def _masked(text: str) -> str:
    result = redact(text)
    if not result.safe:
        raise RedactionError("unsafe text field")
    return result.prompt_preview


def _redact_value(value):
    """Recursively mask strings inside attributes/events structures."""
    if isinstance(value, str):
        return _masked(value)
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    return value  # numbers / bools / None carry no text


def redact_span(span: dict) -> dict:
    """Return a copy of `span` with every free-text field masked."""
    clean = dict(span)
    for field_name in _TEXT_FIELDS:
        if isinstance(clean.get(field_name), str):
            clean[field_name] = _masked(clean[field_name])
    if "attributes" in clean:
        clean["attributes"] = _redact_value(clean["attributes"])
    if "events" in clean:
        clean["events"] = _redact_value(clean["events"])
    return clean


def _summarize(spans: list[dict]) -> dict:
    """Flight summary = the list-endpoint fields (contracts/http.md)."""
    preview = ""
    for span in spans:  # prefer the llm span's preview, else first non-empty
        if span.get("kind") == "llm" and span.get("prompt_preview"):
            preview = span["prompt_preview"]
            break
    if not preview:
        preview = next(
            (span["prompt_preview"] for span in spans if span.get("prompt_preview")),
            "",
        )
    return {
        "start_time": min(span["start_time"] for span in spans),
        "end_time": max(span["end_time"] for span in spans),
        "cost_usd": round(sum(float(span.get("cost_usd", 0.0)) for span in spans), 6),
        "status": "error" if any(s["status"] == "error" for s in spans) else "ok",
        "prompt_preview": preview,
    }


def _ttl_epoch(now: float | None = None) -> int:
    days = int(os.environ.get("VAULT_TTL_DAYS", _DEFAULT_TTL_DAYS))
    return int((now if now is not None else time.time()) + days * 86400)


def ingest(tenant_id: str, body: object, store) -> dict:
    """Run the pipeline for an authenticated tenant. Returns a Lambda-proxy
    response dict; storage errors propagate for the handler's 500."""
    try:
        spans = validate.validate_batch(body, tenant_id)
    except validate.InvalidBatch:
        return errors.error_response("invalid")

    try:
        clean_spans = [redact_span(span) for span in spans]
    except RedactionError:
        return errors.error_response("redaction_failed")  # nothing stored

    trace_id = clean_spans[0]["trace_id"]
    store.put_flight(
        tenant_id=tenant_id,
        trace_id=trace_id,
        spans=clean_spans,
        summary=_summarize(clean_spans),
        expires_at=_ttl_epoch(),
    )
    return errors.json_response(202, {"accepted": True, "trace_id": trace_id})
