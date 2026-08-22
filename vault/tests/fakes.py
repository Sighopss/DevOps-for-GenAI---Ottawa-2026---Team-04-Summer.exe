"""boto3-shaped in-memory fakes. No AWS, no network, no boto3 import."""

from __future__ import annotations

import json


class FakeS3Client:
    """Mimics boto3 s3 client put_object; records everything written."""

    def __init__(self, fail=False):
        self.objects: dict[str, bytes] = {}
        self.calls: list[dict] = []
        self.fail = fail

    def put_object(self, **kwargs):
        if self.fail:
            raise RuntimeError("s3 unavailable")
        self.calls.append(kwargs)
        self.objects[kwargs["Key"]] = kwargs["Body"]
        return {}

    def stored_json(self, key: str) -> dict:
        return json.loads(self.objects[key].decode("utf-8"))

    def dump_all(self) -> str:
        """Every byte at rest, for no-PII-at-rest assertions."""
        return "\n".join(body.decode("utf-8") for body in self.objects.values())


class FakeTable:
    """Mimics a boto3 DynamoDB Table resource (put_item / get_item)."""

    def __init__(self, fail=False):
        self.items: dict[tuple[str, str], dict] = {}
        self.fail = fail

    def put_item(self, Item):
        if self.fail:
            raise RuntimeError("dynamo unavailable")
        self.items[(Item["tenant_id"], Item["trace_id"])] = Item
        return {}

    def get_item(self, Key):
        item = self.items.get((Key["tenant_id"], Key["trace_id"]))
        return {"Item": item} if item is not None else {}

    def query(self, KeyConditionExpression, ExpressionAttributeValues, **kwargs):
        """Supports the one expression shape vault uses:
        'tenant_id = :t AND begins_with(trace_id, :p)' (:p optional)."""
        if self.fail:
            raise RuntimeError("dynamo unavailable")
        tenant = ExpressionAttributeValues[":t"]
        prefix = ExpressionAttributeValues.get(":p", "")
        matches = [
            item
            for (item_tenant, sort_key), item in sorted(self.items.items())
            if item_tenant == tenant and sort_key.startswith(prefix)
        ]
        return {"Items": matches}

    def dump_all(self) -> str:
        return json.dumps(list(self.items.values()), default=str)


def fake_secret_fetch(secrets: dict[str, dict]):
    """Returns a fetch(arn) callable over {arn: {"tenant_id","key"}}."""

    def fetch(arn: str) -> str:
        return json.dumps(secrets[arn])

    return fetch
