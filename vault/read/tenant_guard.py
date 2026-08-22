"""Extract the caller's identity from the (gateway-verified) JWT claims and
decide 200 / 403 / 404 for a trace.

Trevor's HTTP API JWT authorizer verifies token signatures before the
Lambda runs — this module never re-verifies, it only reads claims. Per
contracts/http.md: a Cognito *access* token passes the authorizer but has
no custom:tenant_id claim — that must fail closed as 401, never open.

403 vs 404 (contract: mismatch -> 403, not 404): the trace is looked up
under the caller's tenant first; on a miss the other tenant's partition is
checked — found there means forbidden, found nowhere means not_found.
"""

from __future__ import annotations

# Contract enum (contracts/span.schema.json tenant_id).
TENANTS = ("tenant-a", "tenant-b")


def caller(event: dict) -> tuple[str, str] | None:
    """(tenant_id, actor) from the JWT claims, or None -> 401."""
    claims = (
        (event.get("requestContext") or {}).get("authorizer", {})
        .get("jwt", {})
        .get("claims", {})
    )
    tenant_id = claims.get("custom:tenant_id")
    if not tenant_id:
        return None  # access token instead of ID token, or foreign JWT
    actor = (
        claims.get("cognito:username")
        or claims.get("username")
        or claims.get("sub")
        or "unknown"
    )
    return str(tenant_id), str(actor)


def locate_flight(tenant_id: str, trace_id: str, get_item) -> tuple[str, dict | None]:
    """('ok', item) | ('forbidden', None) | ('not_found', None).

    `get_item(tenant, trace)` returns the Dynamo flight item or None."""
    item = get_item(tenant_id, trace_id)
    if item is not None:
        return "ok", item
    for other in TENANTS:
        if other != tenant_id and get_item(other, trace_id) is not None:
            return "forbidden", None
    return "not_found", None
