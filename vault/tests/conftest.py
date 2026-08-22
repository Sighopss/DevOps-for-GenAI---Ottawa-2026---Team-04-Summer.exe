"""Shared helpers for vault tests."""

import pytest

TRACE_ID = "a" * 32


def make_span(**overrides) -> dict:
    span = {
        "trace_id": TRACE_ID,
        "span_id": "1111111111111111",
        "parent_id": None,
        "tenant_id": "tenant-a",
        "kind": "http",
        "name": "demo.ask",
        "status": "ok",
        "start_time": "2026-08-18T18:00:00.000Z",
        "end_time": "2026-08-18T18:00:01.200Z",
        "cost_usd": 0.0,
    }
    span.update(overrides)
    return span


@pytest.fixture
def store_env(monkeypatch):
    monkeypatch.setenv("BUCKET", "test-bucket")
    monkeypatch.setenv("TABLE", "test-table")
    monkeypatch.delenv("KEY_ARN", raising=False)
