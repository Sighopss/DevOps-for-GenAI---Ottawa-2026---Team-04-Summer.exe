"""List and detail routes: contract shapes, tenant scoping, limit rules."""

import json

from vault.handlers import read as read_handler
from vault.tests.read.conftest import TRACE_A, TRACE_B, jwt_event


def _call(event, store):
    return read_handler.handler(event, None, store=store)


def test_list_returns_only_own_tenant(seeded):
    response = _call(jwt_event("/v1/traces"), seeded)
    assert response["statusCode"] == 200
    flights = json.loads(response["body"])["flights"]
    assert [flight["trace_id"] for flight in flights] == [TRACE_A]
    row = flights[0]
    assert set(row) == {
        "trace_id", "tenant_id", "start_time", "end_time",
        "cost_usd", "status", "prompt_preview",
    }
    assert row["cost_usd"] == 0.0021
    assert row["prompt_preview"] == "User [EMAIL] asked about [SSN]"


def test_list_limit_clamped_to_50(seeded):
    response = _call(jwt_event("/v1/traces", limit="500"), seeded)
    assert response["statusCode"] == 200  # clamped, not an error


def test_list_bad_limit_400(seeded):
    for bad in ("abc", "0", "-3", ""):
        response = _call(jwt_event("/v1/traces", limit=bad), seeded)
        assert response["statusCode"] == 400, f"limit={bad!r}"
        assert json.loads(response["body"])["error"]["code"] == "invalid"


def test_detail_returns_full_flight(seeded):
    response = _call(
        jwt_event(f"/v1/traces/{TRACE_A}", trace_id=TRACE_A), seeded
    )
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["trace_id"] == TRACE_A
    assert body["tenant_id"] == "tenant-a"
    assert isinstance(body["expires_at"], int)
    assert len(body["spans"]) == 2
    kinds = {span["kind"] for span in body["spans"]}
    assert kinds == {"http", "llm"}


def test_detail_never_contains_raw_pii(seeded):
    response = _call(
        jwt_event(f"/v1/traces/{TRACE_A}", trace_id=TRACE_A), seeded
    )
    assert "user@example.com" not in response["body"]
    assert "123-45-6789" not in response["body"]


def test_unknown_trace_404(seeded):
    unknown = "f" * 32
    response = _call(jwt_event(f"/v1/traces/{unknown}", trace_id=unknown), seeded)
    assert response["statusCode"] == 404
    assert json.loads(response["body"])["error"]["code"] == "not_found"


def test_unknown_route_404(seeded):
    response = _call(jwt_event("/v1/other"), seeded)
    assert response["statusCode"] == 404


def test_store_failure_500_fixed_body(seeded):
    seeded._table.fail = True
    response = _call(jwt_event("/v1/traces"), seeded)
    assert response["statusCode"] == 500
    assert json.loads(response["body"]) == {
        "error": {"code": "internal", "message": "internal error"}
    }
