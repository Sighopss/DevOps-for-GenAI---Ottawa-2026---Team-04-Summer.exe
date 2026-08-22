"""Exhaustive DynamoDB Query pagination.

A single `Table.query` returns at most ~1 MB of items with a
`LastEvaluatedKey` when more remain. Reading only the first page silently
truncates — for a tenant's flight list or a trace's audit trail that is a
correctness/security bug (missing flights, an incomplete audit record), and
an in-memory fake never surfaces it. `query_all` follows `LastEvaluatedKey`
until the partition is exhausted.
"""

from __future__ import annotations

# Safety bound: a single tenant/trace partition should never approach this;
# it caps a pathological/hostile partition rather than looping unboundedly.
_MAX_PAGES = 1000


def query_all(table, **query_kwargs) -> list[dict]:
    """Run `table.query(**query_kwargs)` across every page, returning all
    Items in Query order (the caller sorts/slices as its contract needs)."""
    items: list[dict] = []
    start_key = None
    for _ in range(_MAX_PAGES):
        params = dict(query_kwargs)
        if start_key is not None:
            params["ExclusiveStartKey"] = start_key
        response = table.query(**params)
        items.extend(response.get("Items", []))
        start_key = response.get("LastEvaluatedKey")
        if not start_key:
            break
    return items
