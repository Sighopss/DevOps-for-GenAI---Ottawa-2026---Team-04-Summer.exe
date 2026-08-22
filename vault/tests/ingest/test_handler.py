"""Lambda handler: HTTP API v2 events end-to-end against fakes."""

import base64
import json

from vault.handlers import ingest as handler_module
from vault.store import FlightStore
from vault.tests.conftest import TRACE_ID, make_span
from vault.tests.fakes import FakeS3Client, FakeTable, fake_secret_fetch

SECRETS = {"arn:a": {"tenant_id": "tenant-a", "key": "key-for-a-1234"}}


def _event(body, key="key-for-a-1234", b64=False):
    raw = json.dumps(body) if isinstance(body, (dict, list)) else body
    if b64:
        raw = base64.b64encode(raw.encode()).decode()
    headers = {"content-type": "application/json"}
    if key is not None:
        headers["x-tenant-key"] = key
    return {
        "version": "2.0",
        "rawPath": "/v1/traces",
        "headers": headers,
        "body": raw,
        "isBase64Encoded": b64,
    }


def _call(event, s3=None, table=None, monkeypatch=None):
    store = FlightStore(s3_client=s3 or FakeS3Client(), table=table or FakeTable())
    return handler_module.handler(
        event, None, store=store, fetch=fake_secret_fetch(SECRETS)
    )


def _env(monkeypatch):
    monkeypatch.setenv("TENANT_A_SECRET_ARN", "arn:a")
    monkeypatch.delenv("TENANT_B_SECRET_ARN", raising=False)


def test_valid_post_returns_202(store_env, monkeypatch):
    _env(monkeypatch)
    response = _call(_event({"spans": [make_span()]}))
    assert response["statusCode"] == 202
    assert json.loads(response["body"])["trace_id"] == TRACE_ID
    assert response["headers"]["content-type"] == "application/json"


def test_base64_body_accepted(store_env, monkeypatch):
    _env(monkeypatch)
    response = _call(_event({"spans": [make_span()]}, b64=True))
    assert response["statusCode"] == 202


def test_missing_key_401_contract_json(store_env, monkeypatch):
    _env(monkeypatch)
    response = _call(_event({"spans": [make_span()]}, key=None))
    assert response["statusCode"] == 401
    assert json.loads(response["body"]) == {
        "error": {"code": "unauthorized", "message": "auth required"}
    }


def test_wrong_key_401(store_env, monkeypatch):
    _env(monkeypatch)
    response = _call(_event({"spans": [make_span()]}, key="nope"))
    assert response["statusCode"] == 401


def test_malformed_json_400_invalid(store_env, monkeypatch):
    _env(monkeypatch)
    response = _call(_event("{not json"))
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["error"]["code"] == "invalid"


def test_store_failure_500_fixed_body_no_leak(store_env, monkeypatch):
    _env(monkeypatch)
    raw_ssn = "123-45-6789"
    event = _event({"spans": [make_span(prompt_preview=f"ssn {raw_ssn}")]})
    response = _call(event, table=FakeTable(fail=True))
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body == {"error": {"code": "internal", "message": "internal error"}}
    assert raw_ssn not in response["body"]


def test_handler_never_writes_pii_to_stdout_or_logs(store_env, monkeypatch, capsys, caplog):
    _env(monkeypatch)
    raw_email, raw_ssn = "user@example.com", "123-45-6789"
    event = _event(
        {"spans": [make_span(prompt_preview=f"reach {raw_email} ssn {raw_ssn}")]}
    )
    _call(event)
    captured = capsys.readouterr()
    for raw in (raw_email, raw_ssn, "key-for-a-1234"):
        assert raw not in captured.out
        assert raw not in captured.err
        assert raw not in caplog.text
