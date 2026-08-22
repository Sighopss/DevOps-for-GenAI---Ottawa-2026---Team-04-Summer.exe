"""Bedrock on-demand USD rates and the cost_usd estimator for the demo's llm span.

Source: AWS Bedrock pricing page, https://aws.amazon.com/bedrock/pricing/
Captured: 2026-08-22, on-demand, us-east-1 (the demo's fixed AWS_REGION default).
Point-in-time. AWS revises Bedrock pricing without notice — re-check the page
above before trusting these numbers for anything beyond a hackathon demo, and
this table is not a substitute for AWS Cost Explorer / real billing (out of
scope per issue #118).

Notes on the individual rates:
  - anthropic.claude-3-5-sonnet-20241022-v2:0 is EOL on Bedrock (see
    docs/AI_INVENTORY.md) and, as of the capture date, only reachable at all
    under AWS's "Public Extended Access" schedule (effective 2025-12-01),
    which prices it above its original GA rate. That EOL/extended-access rate
    is what is recorded here because it is what a live call actually bills.
  - amazon.nova-lite-v1:0 is Nova Lite's published on-demand rate.
  - amazon.titan-embed-text-v2:0 is billed on input tokens only (no
    generated-output cost for an embedding call); output_usd_per_1k is 0.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal
from typing import NamedTuple

log = logging.getLogger("demo_app.pricing")

RATE_SOURCE = "https://aws.amazon.com/bedrock/pricing/ (on-demand, us-east-1)"
RATE_TABLE_AS_OF = "2026-08-22"

# Cost is quantized to this many decimal places before being handed back as a
# float, so the string round-trip `Decimal(str(cost_usd))` done by
# vault/store/keys.py when writing DynamoDB does not pick up binary-float
# noise (e.g. 0.0006720000000000001). 8dp (a hundredth of a cent's hundredth)
# keeps resolution on Nova Lite's sub-cent-per-1K rates without rounding a
# real, small call down to a misleading 0.0.
_QUANTUM = Decimal("0.00000001")


@dataclass(frozen=True)
class ModelRate:
    input_usd_per_1k: Decimal
    output_usd_per_1k: Decimal


# Keep this table's key set a superset of demo_app.bedrock.ALLOWED_CONVERSE_MODEL_IDS
# plus the embed model id — a model that can be invoked must have a rate.
RATE_TABLE: dict[str, ModelRate] = {
    "anthropic.claude-3-5-sonnet-20241022-v2:0": ModelRate(
        input_usd_per_1k=Decimal("0.006"),
        output_usd_per_1k=Decimal("0.03"),
    ),
    "amazon.nova-lite-v1:0": ModelRate(
        input_usd_per_1k=Decimal("0.00006"),
        output_usd_per_1k=Decimal("0.00024"),
    ),
    "amazon.titan-embed-text-v2:0": ModelRate(
        input_usd_per_1k=Decimal("0.00002"),
        output_usd_per_1k=Decimal("0"),
    ),
}


class CostEstimate(NamedTuple):
    usd: float
    """Non-negative USD estimate. 0.0 when known=False — see `note`."""

    known: bool
    """True when `usd` came from a rate-table entry; False on the fallback."""

    note: str
    """Human-readable provenance, safe to log or store as a span attribute."""


def estimate_cost_usd(model_id: str, *, input_tokens: int, output_tokens: int) -> CostEstimate:
    """Estimate the USD cost of one converse call from real token counts.

    Never silently returns 0.0 for a model AWS actually billed: an unknown
    model id still returns 0.0 (there is no rate to compute from) but is
    flagged `known=False` with a `note` explaining why, so callers can log it
    and surface it on the span instead of presenting it as a real $0 charge.
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")

    rate = RATE_TABLE.get(model_id)
    if rate is None:
        note = (
            f"cost_usd estimate-unavailable: no pricing entry for model_id={model_id!r} "
            f"(source: {RATE_SOURCE}, as of {RATE_TABLE_AS_OF}) — add one to "
            "demo_app.pricing.RATE_TABLE"
        )
        log.error(note)
        return CostEstimate(usd=0.0, known=False, note=note)

    raw = (Decimal(input_tokens) / 1000 * rate.input_usd_per_1k) + (
        Decimal(output_tokens) / 1000 * rate.output_usd_per_1k
    )
    quantized = raw.quantize(_QUANTUM, rounding=ROUND_HALF_EVEN)
    note = (
        f"cost_usd estimated from {input_tokens} input + {output_tokens} output tokens "
        f"at {model_id} rates ${rate.input_usd_per_1k}/1K in, ${rate.output_usd_per_1k}/1K out "
        f"(source: {RATE_SOURCE}, as of {RATE_TABLE_AS_OF})"
    )
    return CostEstimate(usd=float(quantized), known=True, note=note)
