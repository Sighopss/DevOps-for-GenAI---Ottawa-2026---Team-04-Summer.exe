"""Issue #99: DynamoDB paginates (~1 MB). Reading only the first page
silently truncates a tenant's flight list and a trace's audit trail.

These use a FakeTable with `page_size` set, so they fail against a
single-`query()` implementation and pass once LastEvaluatedKey is followed.
"""

from decimal import Decimal

from vault.audit import list_events, record
from vault.read.store_read import ReadStore
from vault.store import keys
from vault.store.paginate import query_all
from vault.tests.fakes import FakeTable

TRACE = "a" * 32


def _seed_flights(table, n, tenant="tenant-a"):
    for i in range(n):
        trace = f"{i:032d}"
        table.put_item(
            Item={
                "tenant_id": tenant,
                "trace_id": keys.flight_sk(trace),
                "flight_trace_id": trace,
                # start_time ascends with i, so the newest are the LAST page
                "start_time": f"2026-08-{(i % 28) + 1:02d}T00:00:{i % 60:02d}.000Z",
                "end_time": "2026-08-22T00:00:01.000Z",
                "cost_usd": Decimal("0.001"),
                "status": "ok",
                "prompt_preview": f"flight {i}",
                "s3_keys": [],
                "span_count": 1,
                "expires_at": 1788020622,
            }
        )


def test_query_all_follows_last_evaluated_key():
    table = FakeTable(page_size=3)
    _seed_flights(table, 10)
    items = query_all(
        table,
        KeyConditionExpression="tenant_id = :t AND begins_with(trace_id, :p)",
        ExpressionAttributeValues={":t": "tenant-a", ":p": keys.FLIGHT_SK_PREFIX},
    )
    assert len(items) == 10  # not 3
    assert table.query_calls == 4  # 3+3+3+1


def test_flight_list_not_truncated_by_paging(store_env):
    table = FakeTable(page_size=3)
    _seed_flights(table, 10)
    store = ReadStore(s3_client=None, table=table)
    rows = store.list_flight_items("tenant-a", limit=50)
    assert len(rows) == 10  # a single-page read would return 3


def test_flight_list_newest_first_across_pages(store_env):
    # The DynamoDB sort key is trace_id, but "newest N" is by start_time —
    # so the newest rows can live on a later page. A single-page read would
    # return the WRONG newest-N, not merely fewer rows.
    table = FakeTable(page_size=3)
    _seed_flights(table, 10)
    store = ReadStore(s3_client=None, table=table)
    rows = store.list_flight_items("tenant-a", limit=3)
    assert [r["flight_trace_id"] for r in rows] == [f"{i:032d}" for i in (9, 8, 7)]


def test_paged_list_stays_tenant_scoped(store_env):
    table = FakeTable(page_size=2)
    _seed_flights(table, 6, tenant="tenant-a")
    _seed_flights(table, 6, tenant="tenant-b")
    store = ReadStore(s3_client=None, table=table)
    rows = store.list_flight_items("tenant-a", limit=50)
    assert len(rows) == 6
    assert {r["tenant_id"] for r in rows} == {"tenant-a"}


def test_audit_trail_not_truncated_by_paging(store_env):
    table = FakeTable(page_size=2)
    for i in range(7):
        record(f"viewer-{i}", "tenant-a", TRACE, table=table)
    events = list_events("tenant-a", TRACE, table=table)
    assert len(events) == 7  # a single-page read would return 2
    assert [e.actor for e in events] == [f"viewer-{i}" for i in range(7)]  # oldest first


def test_paged_audit_stays_scoped_to_tenant_and_trace(store_env):
    table = FakeTable(page_size=2)
    for i in range(5):
        record(f"a-{i}", "tenant-a", TRACE, table=table)
    for i in range(5):
        record(f"b-{i}", "tenant-b", TRACE, table=table)  # same trace id
        record(f"other-{i}", "tenant-a", "b" * 32, table=table)
    events = list_events("tenant-a", TRACE, table=table)
    assert [e.actor for e in events] == [f"a-{i}" for i in range(5)]
