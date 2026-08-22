"""Load TraceVault span schema: product contracts, scratchpad draft, or embed."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

FALLBACK_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://tracevault.dev/schemas/span.json",
    "title": "TraceVaultSpan",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "trace_id",
        "span_id",
        "tenant_id",
        "kind",
        "name",
        "status",
        "start_time",
        "end_time",
    ],
    "properties": {
        "trace_id": {"type": "string", "minLength": 16, "maxLength": 64},
        "span_id": {"type": "string", "minLength": 8, "maxLength": 32},
        "parent_id": {"type": ["string", "null"]},
        "tenant_id": {"type": "string", "enum": ["tenant-a", "tenant-b"]},
        "kind": {"type": "string", "enum": ["llm", "tool", "rag", "http"]},
        "name": {"type": "string", "minLength": 1, "maxLength": 128},
        "status": {"type": "string", "enum": ["ok", "error"]},
        "start_time": {"type": "string", "format": "date-time"},
        "end_time": {"type": "string", "format": "date-time"},
        "gen_ai.request.model": {"type": "string"},
        "gen_ai.usage.input_tokens": {"type": "integer", "minimum": 0},
        "gen_ai.usage.output_tokens": {"type": "integer", "minimum": 0},
        "cost_usd": {"type": "number", "minimum": 0},
        "error_message": {"type": ["string", "null"]},
        "attributes": {"type": "object", "additionalProperties": True},
        "events": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "timestamp"],
                "properties": {
                    "name": {"type": "string"},
                    "timestamp": {"type": "string", "format": "date-time"},
                    "attributes": {"type": "object"},
                },
            },
        },
        "prompt_preview": {"type": "string", "maxLength": 200},
        "prompt_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
    },
}


class SpanSchemaError(ValueError):
    """Span failed TraceVault JSON Schema validation."""


def _schema_candidates() -> list[Path]:
    here = Path(__file__).resolve()
    roots = [Path.cwd().resolve(), *here.parents]
    paths: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        for rel in (
            Path("contracts") / "span.schema.json",
        ):
            candidate = (root / rel).resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            paths.append(candidate)
    return paths


def load_span_schema() -> dict[str, Any]:
    for path in _schema_candidates():
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    return FALLBACK_SCHEMA


def validate_span(span: dict[str, Any]) -> None:
    schema = load_span_schema()
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(span), key=lambda err: list(err.path))
    if errors:
        raise SpanSchemaError("span failed schema validation")
