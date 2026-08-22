"""list_events(): ordering, scoping, and isolation from flights and tenants."""

from types import SimpleNamespace

from vault.audit import list_events, log, record
from vault.store import keys
from vault.tests.fakes import FakeTable

TRACE_A = "a" * 32
TRACE_B = "b" * 32


def test_lists_own_events_oldest_first(store_env):
    table = FakeTable()
    first = record("user-1", "tenant-a", TRACE_A, table=table)
    second = record("user-2", "tenant-a", TRACE_A, table=table)
    events = list_events("tenant-a", TRACE_A, table=table)
    assert [event.actor for event in events] == ["user-1", "user-2"]
    assert events[0].ts <= events[1].ts
    assert (first.ts, second.ts) == (events[0].ts, events[1].ts)


def test_other_tenant_events_never_listed(store_env):
    table = FakeTable()
    record("a-user", "tenant-a", TRACE_A, table=table)
    record("b-user", "tenant-b", TRACE_A, table=table)  # same trace id!
    events = list_events("tenant-a", TRACE_A, table=table)
    assert [event.actor for event in events] == ["a-user"]


def test_other_trace_events_never_listed(store_env):
    table = FakeTable()
    record("actor", "tenant-a", TRACE_A, table=table)
    record("actor", "tenant-a", TRACE_B, table=table)
    events = list_events("tenant-a", TRACE_A, table=table)
    assert len(events) == 1
    assert events[0].trace_id == TRACE_A


def test_flight_items_never_appear_as_audit_events(store_env):
    table = FakeTable()
    # A flight summary row for the same trace shares the partition…
    table.put_item(
        Item={
            "tenant_id": "tenant-a",
            "trace_id": keys.flight_sk(TRACE_A),
            "flight_trace_id": TRACE_A,
            "prompt_preview": "User [EMAIL] asked",
        }
    )
    record("actor", "tenant-a", TRACE_A, table=table)
    events = list_events("tenant-a", TRACE_A, table=table)
    # …but the a# prefix keeps it out of the audit listing.
    assert len(events) == 1
    assert events[0].actor == "actor"


def test_empty_when_no_events(store_env):
    assert list_events("tenant-a", TRACE_A, table=FakeTable()) == []


def test_same_microsecond_events_keep_write_order(store_env, monkeypatch):
    """Two events inside one clock tick still list oldest-first.

    The wall clock behind `ts` is microsecond-resolution at best — on Windows
    it repeats the same value for ~15ms — so back-to-back audit writes share a
    `ts` routinely, and the audit GET does exactly that (record, then list).
    Pinning the clock reproduces it on every platform; pinning the entropy
    suffix so the second row sorts first makes the failure deterministic
    rather than a coin flip.
    """
    monkeypatch.setattr(log.time, "time_ns", lambda: 1_800_000_000_123_456_000)
    suffixes = iter(["ffffffff", "00000000"])
    monkeypatch.setattr(
        log.uuid, "uuid4", lambda: SimpleNamespace(hex=next(suffixes))
    )

    table = FakeTable()
    first = record("user-1", "tenant-a", TRACE_A, table=table)
    second = record("user-2", "tenant-a", TRACE_A, table=table)
    assert first.ts == second.ts  # the tick really did not advance

    events = list_events("tenant-a", TRACE_A, table=table)
    assert [event.actor for event in events] == ["user-1", "user-2"]
