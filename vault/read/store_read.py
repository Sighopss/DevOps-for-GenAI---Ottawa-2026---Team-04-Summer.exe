"""Read-side storage access: flight items from Dynamo, span payloads from S3.

Same lazy-boto3 discipline as the rest of vault: Lambda wires real clients,
tests inject fakes; nothing imports boto3 at module load.
"""

from __future__ import annotations

import json
import os
from decimal import Decimal

from vault.store import keys
from vault.store.paginate import query_all


class ReadStore:
    def __init__(self, s3_client=None, table=None):
        self._s3 = s3_client
        self._table = table

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

    @property
    def table(self):
        return self._table_or_default()

    def get_flight_item(self, tenant_id: str, trace_id: str) -> dict | None:
        response = self._table_or_default().get_item(
            Key={"tenant_id": tenant_id, "trace_id": keys.flight_sk(trace_id)}
        )
        return response.get("Item")

    def list_flight_items(self, tenant_id: str, limit: int) -> list[dict]:
        # Read every page before sorting: the DynamoDB sort key is the
        # trace_id (`t#…`), but "newest `limit`" is by start_time, so the
        # top-N can be spread across pages. A single-page read would return
        # the wrong newest-N, not merely a truncated one.
        items = query_all(
            self._table_or_default(),
            KeyConditionExpression="tenant_id = :t AND begins_with(trace_id, :p)",
            ExpressionAttributeValues={":t": tenant_id, ":p": keys.FLIGHT_SK_PREFIX},
        )
        items.sort(key=lambda item: str(item.get("start_time", "")), reverse=True)
        return items[:limit]

    def load_spans(self, s3_keys: list[str]) -> list[dict]:
        spans: list[dict] = []
        bucket = os.environ["BUCKET"]
        s3 = self._s3_or_default()
        for key in s3_keys:
            body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
            spans.extend(json.loads(body.decode("utf-8"))["spans"])
        return spans


def flight_row(item: dict) -> dict:
    """One flights[] entry — exactly the contract's list fields."""
    return {
        "trace_id": str(item["flight_trace_id"]),
        "tenant_id": str(item["tenant_id"]),
        "start_time": str(item["start_time"]),
        "end_time": str(item["end_time"]),
        "cost_usd": float(Decimal(str(item["cost_usd"]))),
        "status": str(item["status"]),
        "prompt_preview": str(item.get("prompt_preview", "")),
    }
