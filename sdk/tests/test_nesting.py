"""Parent http, child rag, child llm — same trace_id, parent_id matches."""

from __future__ import annotations

from tracevault import TraceVaultClient, start_span


def test_http_rag_llm_nesting() -> None:
    client = TraceVaultClient(tenant_id="tenant-a")
    with start_span(client, kind="http", name="POST /ask"):
        with start_span(client, kind="rag", name="retrieve"):
            pass
        with start_span(client, kind="llm", name="chat", model="test-model"):
            pass

    assert len(client.spans) == 3
    by_kind = {span["kind"]: span for span in client.spans}
    http = by_kind["http"]
    rag = by_kind["rag"]
    llm = by_kind["llm"]

    trace_ids = {span["trace_id"] for span in client.spans}
    assert len(trace_ids) == 1
    assert http["parent_id"] is None
    assert rag["parent_id"] == http["span_id"]
    assert llm["parent_id"] == http["span_id"]
    assert llm["gen_ai.request.model"] == "test-model"
    assert rag["trace_id"] == http["trace_id"]
    assert llm["trace_id"] == http["trace_id"]
