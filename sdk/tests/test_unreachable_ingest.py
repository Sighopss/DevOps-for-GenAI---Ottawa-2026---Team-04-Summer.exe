"""Unreachable ingest parks the flight locally and does not raise (#49)."""

from __future__ import annotations

import json
from pathlib import Path

from tracevault import TraceVaultClient, start_span

_LAST_FLIGHT = Path(__file__).resolve().parents[1] / ".last-flight.json"


def test_unreachable_ingest_writes_last_flight_without_raising() -> None:
    if _LAST_FLIGHT.exists():
        _LAST_FLIGHT.unlink()

    client = TraceVaultClient(
        tenant_id="tenant-a",
        ingest_url="http://127.0.0.1:1",  # nothing listens
        tenant_key="dummy",
        timeout=0.2,
    )
    with start_span(client, kind="http", name="deploy-gate-demo"):
        pass

    client.flush()  # must not raise

    assert _LAST_FLIGHT.is_file()
    spans = json.loads(_LAST_FLIGHT.read_text(encoding="utf-8"))
    assert isinstance(spans, list)
    assert len(spans) == 1
    assert spans[0]["name"] == "deploy-gate-demo"
