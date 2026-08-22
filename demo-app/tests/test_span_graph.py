"""Fake-bedrock span graph: 4 spans, one trace_id, parent_id. No AWS network."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from demo_app.main import run
from demo_app.emitter import load_emitter
from tracevault import TraceVaultClient

LAST_FLIGHT = Path(__file__).resolve().parents[2] / "sdk" / ".last-flight.json"


@pytest.fixture
def fake_bedrock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRACEVAULT_FAKE_BEDROCK", "1")
    monkeypatch.delenv("TRACEVAULT_INGEST_URL", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("AWS_SESSION_TOKEN", raising=False)

    def _no_aws(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("no AWS network")

    monkeypatch.setattr("demo_app.bedrock.boto3.client", _no_aws)


def test_default_emitter_is_the_real_sdk(fake_bedrock: None) -> None:
    client, _start_span = load_emitter("tenant-a")
    assert type(client) is TraceVaultClient
    assert client.ingest_url is None


def test_span_graph(fake_bedrock: None) -> None:
    answer, spans = run(
        question="What is the retention TTL?",
        tenant_id="tenant-a",
        pii=False,
    )
    assert answer
    assert len(spans) == 4
    assert len({span["trace_id"] for span in spans}) == 1
    by_kind = {span["kind"]: span for span in spans}
    assert set(by_kind) == {"http", "rag", "tool", "llm"}
    http = by_kind["http"]
    assert http["name"] == "demo.ask"
    assert http["parent_id"] is None
    assert http["tenant_id"] == "tenant-a"
    assert by_kind["rag"]["name"] == "demo.retrieve"
    assert by_kind["tool"]["name"] == "demo.get_doc_metadata"
    assert by_kind["llm"]["name"] == "demo.converse"
    for kind in ("rag", "tool", "llm"):
        child = by_kind[kind]
        assert child["parent_id"] == http["span_id"]
        assert child["trace_id"] == http["trace_id"]
        assert child["tenant_id"] == "tenant-a"
    llm = by_kind["llm"]
    assert llm["gen_ai.usage.input_tokens"] == 1
    assert llm["gen_ai.usage.output_tokens"] == 1
    assert llm["cost_usd"] == 0
    assert LAST_FLIGHT.is_file()
    dumped = json.loads(LAST_FLIGHT.read_text(encoding="utf-8"))
    assert len(dumped) == 4
    assert dumped[0]["trace_id"] == http["trace_id"]


def test_pii_marks_llm_without_logging_prompt(
    fake_bedrock: None,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with caplog.at_level(logging.DEBUG):
        _answer, spans = run(
            question="What is tenant isolation?",
            tenant_id="tenant-a",
            pii=True,
        )
    captured = caplog.text + capsys.readouterr().out + capsys.readouterr().err
    assert "user@example.com" not in captured
    assert "123-45-6789" not in captured
    llm = next(span for span in spans if span["kind"] == "llm")
    assert llm.get("prompt_hash")
    preview = llm.get("prompt_preview") or ""
    assert "user@example.com" not in preview
    assert "123-45-6789" not in preview
    assert "[EMAIL]" in preview
    assert "[SSN]" in preview
