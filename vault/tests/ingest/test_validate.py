"""Batch validation: schema essentials enforced, fail-closed on unknowns."""

import pytest

from vault.ingest.validate import InvalidBatch, validate_batch
from vault.tests.conftest import make_span


def _batch(*spans):
    return {"spans": list(spans)}


def test_valid_batch_passes():
    spans = validate_batch(_batch(make_span()), "tenant-a")
    assert len(spans) == 1


def test_full_fixture_shaped_span_passes():
    span = make_span(
        kind="llm",
        **{
            "gen_ai.request.model": "anthropic.claude-sonnet-4-20250514-v1:0",
            "gen_ai.usage.input_tokens": 120,
            "gen_ai.usage.output_tokens": 40,
        },
        cost_usd=0.0021,
        prompt_preview="User [EMAIL] asked about [SSN]",
        prompt_hash="a" * 64,
        attributes={"contains_pii": True},
    )
    assert validate_batch(_batch(span), "tenant-a")


@pytest.mark.parametrize("missing", ["trace_id", "tenant_id", "kind", "status"])
def test_missing_required_field_rejected(missing):
    span = make_span()
    del span[missing]
    with pytest.raises(InvalidBatch):
        validate_batch(_batch(span), "tenant-a")


def test_unknown_field_rejected_fail_closed():
    # additionalProperties: false — an unvalidated field could smuggle PII.
    with pytest.raises(InvalidBatch):
        validate_batch(_batch(make_span(raw_prompt="ssn 123-45-6789")), "tenant-a")


def test_wrong_enum_rejected():
    with pytest.raises(InvalidBatch):
        validate_batch(_batch(make_span(kind="grafana")), "tenant-a")
    with pytest.raises(InvalidBatch):
        validate_batch(_batch(make_span(tenant_id="tenant-c")), "tenant-a")


def test_span_tenant_must_match_key_tenant():
    # tenant-b key must not write spans labeled tenant-a (injection).
    with pytest.raises(InvalidBatch):
        validate_batch(_batch(make_span(tenant_id="tenant-a")), "tenant-b")


def test_mixed_trace_ids_rejected():
    with pytest.raises(InvalidBatch):
        validate_batch(
            _batch(make_span(), make_span(trace_id="b" * 32, span_id="2222222222222222")),
            "tenant-a",
        )


def test_empty_and_malformed_bodies_rejected():
    for body in ({}, {"spans": []}, {"spans": "nope"}, [], None, "spans"):
        with pytest.raises(InvalidBatch):
            validate_batch(body, "tenant-a")


def test_bad_prompt_hash_rejected():
    with pytest.raises(InvalidBatch):
        validate_batch(_batch(make_span(prompt_hash="XYZ")), "tenant-a")


def test_oversize_batch_rejected():
    spans = [make_span(span_id=f"{i:016d}") for i in range(101)]
    with pytest.raises(InvalidBatch):
        validate_batch({"spans": spans}, "tenant-a")


def test_error_messages_never_contain_values():
    span = make_span(raw_prompt="ssn 123-45-6789 mail user@example.com")
    with pytest.raises(InvalidBatch) as excinfo:
        validate_batch(_batch(span), "tenant-a")
    assert "123-45-6789" not in str(excinfo.value)
    assert "user@example.com" not in str(excinfo.value)
