"""FlightStore: key layout, item shape, commit-point ordering."""

from decimal import Decimal

import pytest

from vault.store import FlightStore, keys
from vault.tests.fakes import FakeS3Client, FakeTable

TRACE = "a" * 32
SUMMARY = {
    "start_time": "2026-08-18T18:00:00.000Z",
    "end_time": "2026-08-18T18:00:01.200Z",
    "cost_usd": 0.0021,
    "status": "ok",
    "prompt_preview": "User [EMAIL] asked about [SSN]",
}


def _put(s3=None, table=None):
    s3 = s3 or FakeS3Client()
    table = table or FakeTable()
    store = FlightStore(s3_client=s3, table=table)
    store.put_flight("tenant-a", TRACE, [{"span_id": "x"}], dict(SUMMARY), 1780000000)
    return s3, table


def test_s3_key_under_tenant_prefix(store_env):
    # IAM only allows PutObject under {tenant}/* — the key must comply.
    s3, _ = _put()
    key = list(s3.objects)[0]
    assert key.startswith(f"tenant-a/{TRACE}/")
    assert key.endswith(".json")


def test_dynamo_item_shape(store_env):
    _, table = _put()
    item = table.items[("tenant-a", keys.flight_sk(TRACE))]
    assert item["flight_trace_id"] == TRACE
    assert isinstance(item["cost_usd"], Decimal)  # DynamoDB rejects float
    assert item["expires_at"] == 1780000000
    assert item["span_count"] == 1


def test_sk_prefixes_separate_flights_from_audit():
    assert keys.flight_sk(TRACE).startswith("t#")
    assert keys.audit_sk(TRACE, "2026-08-18T18:00:00Z").startswith(f"a#{TRACE}#")


def test_s3_written_before_dynamo_commit(store_env):
    # Dynamo failure -> exception propagates, S3 orphan is unreachable
    # (reads resolve through the Dynamo item), nothing half-visible.
    s3 = FakeS3Client()
    with pytest.raises(RuntimeError):
        _put(s3=s3, table=FakeTable(fail=True))
    assert len(s3.objects) == 1  # orphan allowed


def test_s3_failure_writes_nothing_anywhere(store_env):
    table = FakeTable()
    with pytest.raises(RuntimeError):
        _put(s3=FakeS3Client(fail=True), table=table)
    assert table.items == {}


def test_kms_headers_added_when_key_arn_set(store_env, monkeypatch):
    monkeypatch.setenv("KEY_ARN", "arn:aws:kms:us-east-1:1:key/k")
    s3, _ = _put()
    call = s3.calls[0]
    assert call["ServerSideEncryption"] == "aws:kms"
    assert call["SSEKMSKeyId"] == "arn:aws:kms:us-east-1:1:key/k"
