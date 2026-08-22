"""FlightStore: put a redacted flight (S3 payload + Dynamo summary).

Order is S3 first, Dynamo second — the Dynamo item is the commit point
(see package docstring). Repeat batches for the same trace merge into the
existing summary: earliest start, latest end, summed cost, error-wins
status, first non-empty preview, appended s3_keys.

boto3 is imported lazily; tests inject boto3-shaped fakes (an S3 client
with put_object and a DynamoDB Table resource with put_item/get_item).
"""

from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal

from vault.store import keys


class FlightStore:
    def __init__(self, s3_client=None, table=None):
        self._s3 = s3_client
        self._table = table

    # -- lazy AWS wiring (Lambda path; tests always inject) ------------------

    def _s3_or_default(self):
        if self._s3 is None:
            import boto3

            self._s3 = boto3.client("s3")
        return self._s3

    def _table_or_default(self):
        if self._table is None:
            import boto3

            self._table = boto3.resource("dynamodb").Table(os.environ["TABLE"])
        return self._table

    # -- write ---------------------------------------------------------------

    def put_flight(
        self,
        tenant_id: str,
        trace_id: str,
        spans: list[dict],
        summary: dict,
        expires_at: int,
    ) -> None:
        batch_id = uuid.uuid4().hex
        key = keys.s3_key(tenant_id, trace_id, batch_id)
        self._put_payload(key, {"spans": spans})

        existing = self._get_item(tenant_id, trace_id)
        if existing:
            summary = _merge_summary(existing, summary)
            s3_keys = list(existing.get("s3_keys", [])) + [key]
            span_count = int(existing.get("span_count", 0)) + len(spans)
        else:
            s3_keys = [key]
            span_count = len(spans)

        item = keys.flight_item(
            tenant_id, trace_id, summary, s3_keys, span_count, expires_at
        )
        self._table_or_default().put_item(Item=item)

    # -- helpers -------------------------------------------------------------

    def _put_payload(self, key: str, payload: dict) -> None:
        bucket = os.environ["BUCKET"]
        kwargs = {
            "Bucket": bucket,
            "Key": key,
            "Body": json.dumps(payload).encode("utf-8"),
            "ContentType": "application/json",
        }
        key_arn = os.environ.get("KEY_ARN")
        if key_arn:
            kwargs["ServerSideEncryption"] = "aws:kms"
            kwargs["SSEKMSKeyId"] = key_arn
        self._s3_or_default().put_object(**kwargs)

    def _get_item(self, tenant_id: str, trace_id: str) -> dict | None:
        response = self._table_or_default().get_item(
            Key={"tenant_id": tenant_id, "trace_id": keys.flight_sk(trace_id)}
        )
        return response.get("Item")


def _merge_summary(existing: dict, incoming: dict) -> dict:
    return {
        "start_time": min(str(existing["start_time"]), incoming["start_time"]),
        "end_time": max(str(existing["end_time"]), incoming["end_time"]),
        "cost_usd": float(Decimal(str(existing["cost_usd"]))) + incoming["cost_usd"],
        "status": "error"
        if "error" in (existing["status"], incoming["status"])
        else "ok",
        "prompt_preview": str(existing.get("prompt_preview") or "")
        or incoming["prompt_preview"],
    }
