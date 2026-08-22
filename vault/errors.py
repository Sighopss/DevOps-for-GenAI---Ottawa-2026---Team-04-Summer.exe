"""Shared error envelope for both Lambdas (issue #17). The contract locks
`{ "error": { "code": ..., "message": ... } }` and five 4xx codes; messages
are fixed strings so they can never carry PII, prompts, or keys.

`forbidden` must read exactly "tenant mismatch" — the 403 example in
contracts/fixtures/tenant-b-forbidden.json locks that body verbatim.
"""

from __future__ import annotations

import json

# code -> (http status, fixed message)
_ERRORS: dict[str, tuple[int, str]] = {
    "unauthorized": (401, "auth required"),
    "forbidden": (403, "tenant mismatch"),
    "not_found": (404, "not found"),
    "invalid": (400, "invalid request"),
    "redaction_failed": (400, "redaction failed; nothing stored"),
    # Not in the contract's 4xx table: storage/unexpected failure. The body
    # keeps the same envelope; the message is fixed and PII-free.
    "internal": (500, "internal error"),
}

_JSON_HEADERS = {"content-type": "application/json"}


def error_response(code: str) -> dict:
    """API Gateway HTTP API v2 Lambda-proxy response for an error code."""
    status, message = _ERRORS[code]
    return {
        "statusCode": status,
        "headers": dict(_JSON_HEADERS),
        "body": json.dumps({"error": {"code": code, "message": message}}),
    }


def json_response(status: int, payload: dict) -> dict:
    """Success envelope with the same headers."""
    return {
        "statusCode": status,
        "headers": dict(_JSON_HEADERS),
        "body": json.dumps(payload),
    }
