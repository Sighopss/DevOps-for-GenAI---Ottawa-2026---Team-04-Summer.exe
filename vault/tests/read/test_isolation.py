"""The judge-path guarantees: 403 not 404, 401 fail-closed, audit writes."""

import json

from vault.handlers import read as read_handler
from vault.tests.read.conftest import TRACE_A, TRACE_B, jwt_event


def _call(event, store):
    return read_handler.handler(event, None, store=store)


def test_cross_tenant_read_is_403_not_404_exact_fixture_body(seeded):
    # Judge path step 3 — and the body is locked verbatim by
    # contracts/fixtures/tenant-b-forbidden.json.
    response = _call(
        jwt_event(f"/v1/traces/{TRACE_A}", tenant="tenant-b",
                  username="tenant-b", trace_id=TRACE_A),
        seeded,
    )
    assert response["statusCode"] == 403
    assert json.loads(response["body"]) == {
        "error": {"code": "forbidden", "message": "tenant mismatch"}
    }


def test_cross_tenant_403_leaks_no_flight_data(seeded):
    response = _call(
        jwt_event(f"/v1/traces/{TRACE_A}", tenant="tenant-b",
                  username="tenant-b", trace_id=TRACE_A),
        seeded,
    )
    assert "spans" not in response["body"]
    assert "[EMAIL]" not in response["body"]


def test_tenant_b_list_never_shows_tenant_a(seeded):
    response = _call(jwt_event("/v1/traces", tenant="tenant-b"), seeded)
    flights = json.loads(response["body"])["flights"]
    assert [flight["trace_id"] for flight in flights] == [TRACE_B]


def test_missing_tenant_claim_401_fail_closed(seeded):
    # An access token passes the gateway authorizer but has no
    # custom:tenant_id — contracts/http.md says fail closed here.
    access_token_claims = {"sub": "u-123", "username": "tenant-a", "scope": "openid"}
    for path in ("/v1/traces", f"/v1/traces/{TRACE_A}", f"/v1/traces/{TRACE_A}/audit"):
        response = _call(jwt_event(path, claims=access_token_claims), seeded)
        assert response["statusCode"] == 401, path
        assert json.loads(response["body"]) == {
            "error": {"code": "unauthorized", "message": "auth required"}
        }


def test_no_authorizer_context_401(seeded):
    response = read_handler.handler(
        {"version": "2.0", "rawPath": "/v1/traces", "requestContext": {}},
        None,
        store=seeded,
    )
    assert response["statusCode"] == 401


def test_audit_get_writes_row_and_returns_it(seeded):
    path = f"/v1/traces/{TRACE_A}/audit"
    first = _call(jwt_event(path, username="alexis-a", trace_id=TRACE_A), seeded)
    assert first["statusCode"] == 200
    events = json.loads(first["body"])["events"]
    assert len(events) == 1  # viewing the trail is itself audited
    assert events[0]["actor"] == "alexis-a"
    assert events[0]["tenant_id"] == "tenant-a"
    assert events[0]["trace_id"] == TRACE_A
    assert set(events[0]) == {"actor", "tenant_id", "trace_id", "ts"}

    second = _call(jwt_event(path, username="alexis-a", trace_id=TRACE_A), seeded)
    assert len(json.loads(second["body"])["events"]) == 2  # oldest first
    two = json.loads(second["body"])["events"]
    assert two[0]["ts"] <= two[1]["ts"]


def test_audit_route_same_403_rule(seeded):
    response = _call(
        jwt_event(f"/v1/traces/{TRACE_A}/audit", tenant="tenant-b",
                  username="tenant-b", trace_id=TRACE_A),
        seeded,
    )
    assert response["statusCode"] == 403
    # Forbidden view attempts do not write into the victim tenant's trail.
    own = _call(jwt_event(f"/v1/traces/{TRACE_A}/audit", trace_id=TRACE_A), seeded)
    events = json.loads(own["body"])["events"]
    assert all(event["actor"] != "tenant-b" for event in events)
