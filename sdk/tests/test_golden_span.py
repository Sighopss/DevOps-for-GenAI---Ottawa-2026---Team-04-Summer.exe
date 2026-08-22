"""Golden span: required keys exist (ids may differ from the fixture)."""

from __future__ import annotations

import json
from pathlib import Path

from tracevault import TraceVaultClient, start_span

REQUIRED = (
    "trace_id",
    "span_id",
    "tenant_id",
    "kind",
    "name",
    "status",
    "start_time",
    "end_time",
)

GOLDEN = Path(__file__).parent / "golden" / "root_span.json"


def test_golden_span_has_required_keys() -> None:
    fixture = json.loads(GOLDEN.read_text(encoding="utf-8"))
    client = TraceVaultClient(tenant_id="tenant-a")
    with start_span(
        client,
        kind="http",
        name="POST /ask",
        attributes={"route": "/ask"},
    ):
        pass

    assert len(client.spans) == 1
    span = client.spans[0]
    for key in REQUIRED:
        assert key in span, f"missing required key {key}"
        assert key in fixture

    assert span["kind"] == "http"
    assert span["name"] == "POST /ask"
    assert span["tenant_id"] == "tenant-a"
    assert span["status"] == "ok"
    assert span["cost_usd"] == 0.0
    assert len(span["trace_id"]) == 32
    assert len(span["span_id"]) == 16
    assert span["start_time"].endswith("Z")
    assert span["end_time"].endswith("Z")
