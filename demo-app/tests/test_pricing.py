"""cost_usd estimator: known-model math, rounding, and the unknown-model fallback."""

from __future__ import annotations

from decimal import Decimal

import pytest

from demo_app import bedrock
from demo_app.pricing import RATE_TABLE, estimate_cost_usd


def test_allowed_converse_models_and_default_embed_model_all_have_rates() -> None:
    # Defense in depth: a model that can actually be invoked must have a
    # price, or a live call silently under-reports cost_usd.
    for model_id in bedrock.ALLOWED_CONVERSE_MODEL_IDS:
        assert model_id in RATE_TABLE, f"{model_id} is invokable but has no rate entry"
    assert bedrock.DEFAULT_EMBED_MODEL_ID in RATE_TABLE


def test_known_model_computes_nonzero_cost_from_real_token_counts() -> None:
    # A realistic-sized RAG answer, not the 1-token fake stub.
    estimate = estimate_cost_usd(
        "amazon.nova-lite-v1:0", input_tokens=612, output_tokens=143
    )
    assert estimate.known is True
    assert estimate.usd > 0.0
    # 612 * 0.00006/1000 + 143 * 0.00024/1000, hand-computed independently of
    # the implementation's Decimal path.
    expected = float(
        (Decimal(612) / 1000 * Decimal("0.00006"))
        + (Decimal(143) / 1000 * Decimal("0.00024"))
    )
    assert estimate.usd == pytest.approx(expected, abs=1e-9)
    assert "amazon.nova-lite-v1:0" in estimate.note


def test_more_expensive_model_costs_more_for_the_same_tokens() -> None:
    nova = estimate_cost_usd("amazon.nova-lite-v1:0", input_tokens=1000, output_tokens=1000)
    sonnet = estimate_cost_usd(
        "anthropic.claude-3-5-sonnet-20241022-v2:0", input_tokens=1000, output_tokens=1000
    )
    assert sonnet.usd > nova.usd


def test_cost_survives_as_a_clean_decimal_string(monkeypatch: pytest.MonkeyPatch) -> None:
    # Guards the DynamoDB Decimal(str(cost_usd)) round trip done in
    # vault/store/keys.py — no float noise like 0.0006720000000000001.
    estimate = estimate_cost_usd("amazon.nova-lite-v1:0", input_tokens=612, output_tokens=143)
    as_decimal = Decimal(str(estimate.usd))
    assert as_decimal == as_decimal.quantize(Decimal("0.00000001"))


def test_zero_tokens_costs_zero_and_is_still_known() -> None:
    estimate = estimate_cost_usd("amazon.nova-lite-v1:0", input_tokens=0, output_tokens=0)
    assert estimate.usd == 0.0
    assert estimate.known is True


def test_negative_tokens_rejected() -> None:
    with pytest.raises(ValueError):
        estimate_cost_usd("amazon.nova-lite-v1:0", input_tokens=-1, output_tokens=0)


def test_unknown_model_id_is_not_silently_zero(caplog: pytest.LogCaptureFixture) -> None:
    import logging

    with caplog.at_level(logging.ERROR, logger="demo_app.pricing"):
        estimate = estimate_cost_usd("some.future-model-id", input_tokens=100, output_tokens=50)

    assert estimate.known is False
    assert estimate.usd == 0.0
    assert "some.future-model-id" in estimate.note
    assert "estimate-unavailable" in estimate.note
    # The fallback logs loudly rather than returning 0.0 with no trace of why.
    assert any("some.future-model-id" in record.message for record in caplog.records)


def test_embed_model_has_no_output_rate() -> None:
    assert RATE_TABLE[bedrock.DEFAULT_EMBED_MODEL_ID].output_usd_per_1k == Decimal("0")
