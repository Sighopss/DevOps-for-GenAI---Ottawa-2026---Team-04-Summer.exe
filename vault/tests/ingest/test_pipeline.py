"""Pipeline: redact-then-store, summary math, fail-closed store guarantee."""

import json

import pytest

from vault.ingest import pipeline
from vault.redact import RedactionError
from vault.store import FlightStore
from vault.tests.conftest import TRACE_ID, make_span
from vault.tests.fakes import FakeS3Client, FakeTable

RAW_EMAIL = "user@example.com"
RAW_SSN = "123-45-6789"


def _run(spans, tenant="tenant-a", s3=None, table=None):
    s3 = s3 if s3 is not None else FakeS3Client()
    table = table if table is not None else FakeTable()
    store = FlightStore(s3_client=s3, table=table)
    response = pipeline.ingest(tenant, {"spans": spans}, store)
    return response, s3, table


def test_happy_path_202(store_env):
    response, s3, table = _run([make_span()])
    assert response["statusCode"] == 202
    body = json.loads(response["body"])
    assert body == {"accepted": True, "trace_id": TRACE_ID}
    assert len(s3.objects) == 1
    assert list(s3.objects)[0].startswith(f"tenant-a/{TRACE_ID}/")
    assert ("tenant-a", f"t#{TRACE_ID}") in table.items


def test_pii_in_any_text_field_never_reaches_rest(store_env):
    spans = [
        make_span(
            name="demo.ask",
            prompt_preview=f"reach {RAW_EMAIL} ssn {RAW_SSN}",
            attributes={
                "note": f"email {RAW_EMAIL}",
                "nested": {"deep": [f"ssn {RAW_SSN}", 42]},
            },
            events=[
                {
                    "name": f"contact {RAW_EMAIL}",
                    "timestamp": "2026-08-18T18:00:00.500Z",
                    "attributes": {"detail": RAW_SSN},
                }
            ],
        )
    ]
    response, s3, table = _run(spans)
    assert response["statusCode"] == 202
    at_rest = s3.dump_all() + table.dump_all()
    assert RAW_EMAIL not in at_rest
    assert RAW_SSN not in at_rest
    assert "[EMAIL]" in at_rest
    assert "[SSN]" in at_rest


def test_summary_fields_and_ttl(store_env, monkeypatch):
    monkeypatch.setenv("VAULT_TTL_DAYS", "7")
    spans = [
        make_span(start_time="2026-08-18T18:00:00.000Z", end_time="2026-08-18T18:00:01.200Z"),
        make_span(
            span_id="cccc333333333333",
            parent_id="1111111111111111",
            kind="llm",
            start_time="2026-08-18T18:00:00.370Z",
            end_time="2026-08-18T18:00:01.150Z",
            cost_usd=0.0021,
            prompt_preview="User [EMAIL] asked about [SSN]",
        ),
    ]
    _, _, table = _run(spans)
    item = table.items[("tenant-a", f"t#{TRACE_ID}")]
    assert item["start_time"] == "2026-08-18T18:00:00.000Z"
    assert item["end_time"] == "2026-08-18T18:00:01.200Z"
    assert float(item["cost_usd"]) == pytest.approx(0.0021)
    assert item["status"] == "ok"
    assert item["prompt_preview"] == "User [EMAIL] asked about [SSN]"
    assert item["span_count"] == 2
    import time

    seven_days = 7 * 86400
    assert abs(int(item["expires_at"]) - (time.time() + seven_days)) < 300


def test_error_status_wins(store_env):
    spans = [make_span(), make_span(span_id="2222222222222222", status="error")]
    _, _, table = _run(spans)
    assert table.items[("tenant-a", f"t#{TRACE_ID}")]["status"] == "error"


def test_cost_and_tokens_persisted_unchanged(store_env):
    span = make_span(
        kind="llm",
        cost_usd=0.0021,
        **{"gen_ai.usage.input_tokens": 120, "gen_ai.usage.output_tokens": 40},
    )
    _, s3, _ = _run([span])
    stored = s3.stored_json(list(s3.objects)[0])["spans"][0]
    assert stored["cost_usd"] == 0.0021
    assert stored["gen_ai.usage.input_tokens"] == 120
    assert stored["gen_ai.usage.output_tokens"] == 40


def test_redaction_failure_stores_nothing(store_env, monkeypatch):
    def unsafe(_text):
        raise RedactionError("forced")

    monkeypatch.setattr(pipeline, "_masked", unsafe)
    response, s3, table = _run([make_span(prompt_preview="anything")])
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["error"]["code"] == "redaction_failed"
    assert s3.objects == {}
    assert table.items == {}


def test_invalid_batch_stores_nothing(store_env):
    response, s3, table = _run([make_span(kind="grafana")])
    assert response["statusCode"] == 400
    assert json.loads(response["body"])["error"]["code"] == "invalid"
    assert s3.objects == {}
    assert table.items == {}


def test_repeat_batch_merges_summary(store_env):
    s3, table = FakeS3Client(), FakeTable()
    _run([make_span(cost_usd=0.001)], s3=s3, table=table)
    _run(
        [
            make_span(
                span_id="2222222222222222",
                cost_usd=0.002,
                end_time="2026-08-18T18:00:02.000Z",
            )
        ],
        s3=s3,
        table=table,
    )
    item = table.items[("tenant-a", f"t#{TRACE_ID}")]
    assert float(item["cost_usd"]) == pytest.approx(0.003)
    assert item["end_time"] == "2026-08-18T18:00:02.000Z"
    assert item["span_count"] == 2
    assert len(item["s3_keys"]) == 2
