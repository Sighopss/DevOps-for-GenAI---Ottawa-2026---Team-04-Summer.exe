"""record(): item shape, TTL, and the only-four-fields guarantee."""

import time

from vault.audit import record
from vault.tests.fakes import FakeTable

TRACE = "a" * 32


def test_record_writes_all_contract_fields(store_env):
    table = FakeTable()
    event = record("tenant-a-user", "tenant-a", TRACE, table=table)
    assert len(table.items) == 1
    ((tenant, sort_key), item) = next(iter(table.items.items()))
    assert tenant == "tenant-a"
    assert sort_key.startswith(f"a#{TRACE}#")
    assert item["actor"] == "tenant-a-user"
    assert item["flight_trace_id"] == TRACE
    assert item["ts"] == event.ts
    assert item["ts"].endswith("Z")


def test_record_carries_ttl(store_env, monkeypatch):
    monkeypatch.setenv("VAULT_TTL_DAYS", "7")
    table = FakeTable()
    record("actor", "tenant-a", TRACE, table=table)
    item = next(iter(table.items.values()))
    assert abs(int(item["expires_at"]) - (time.time() + 7 * 86400)) < 300


def test_same_instant_events_do_not_overwrite(store_env):
    table = FakeTable()
    record("actor", "tenant-a", TRACE, table=table)
    record("actor", "tenant-a", TRACE, table=table)
    assert len(table.items) == 2  # entropy suffix keeps SKs unique


def test_audit_row_holds_no_prompt_data(store_env):
    table = FakeTable()
    record("actor", "tenant-a", TRACE, table=table)
    item = next(iter(table.items.values()))
    assert set(item) == {
        "tenant_id",
        "trace_id",
        "actor",
        "flight_trace_id",
        "ts",
        "expires_at",
    }


def test_event_to_dict_matches_contract(store_env):
    event = record("actor", "tenant-a", TRACE, table=FakeTable())
    assert set(event.to_dict()) == {"actor", "tenant_id", "trace_id", "ts"}
