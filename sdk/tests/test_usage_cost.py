"""set_usage: cost_usd/token setters, and merging extra attributes (issue #118)."""

from __future__ import annotations

from tracevault import TraceVaultClient, start_span


def test_set_usage_sets_tokens_and_cost() -> None:
    client = TraceVaultClient(tenant_id="tenant-a")
    with start_span(client, kind="llm", name="chat", model="m") as span:
        span.set_usage(input_tokens=612, output_tokens=143, cost_usd=0.00007104)

    recorded = client.spans[0]
    assert recorded["gen_ai.usage.input_tokens"] == 612
    assert recorded["gen_ai.usage.output_tokens"] == 143
    assert recorded["cost_usd"] == 0.00007104


def test_set_usage_merges_attributes_without_clobbering_span_attributes() -> None:
    client = TraceVaultClient(tenant_id="tenant-a")
    with start_span(
        client,
        kind="llm",
        name="chat",
        model="m",
        attributes={"rag.top_k": 2},
    ) as span:
        span.set_usage(cost_usd=0.01, attributes={"cost.known": True, "cost.note": "estimated"})

    attrs = client.spans[0]["attributes"]
    assert attrs == {"rag.top_k": 2, "cost.known": True, "cost.note": "estimated"}


def test_set_usage_attributes_default_none_leaves_no_attributes_key() -> None:
    client = TraceVaultClient(tenant_id="tenant-a")
    with start_span(client, kind="llm", name="chat", model="m") as span:
        span.set_usage(cost_usd=0.0)

    assert "attributes" not in client.spans[0]
