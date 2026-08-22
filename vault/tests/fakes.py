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

    def get_object(self, Bucket, Key):
        import io

        if self.fail:
            raise RuntimeError("s3 unavailable")
        return {"Body": io.BytesIO(self.objects[Key])}

    def stored_json(self, key: str) -> dict:
        return json.loads(self.objects[key].decode("utf-8"))

    def dump_all(self) -> str:
        """Every byte at rest, for no-PII-at-rest assertions."""
        return "\n".join(body.decode("utf-8") for body in self.objects.values())


class FakeTable:
    """Mimics a boto3 DynamoDB Table resource (put_item / get_item)."""

    def __init__(self, fail=False, page_size=None):
        self.items: dict[tuple[str, str], dict] = {}
        self.fail = fail
        self.page_size = page_size  # None = single page (legacy behaviour)
        self.query_calls = 0

    def put_item(self, Item):
        if self.fail:
            raise RuntimeError("dynamo unavailable")
        self.items[(Item["tenant_id"], Item["trace_id"])] = Item
        return {}

    def get_item(self, Key):
        item = self.items.get((Key["tenant_id"], Key["trace_id"]))
        return {"Item": item} if item is not None else {}

    def query(self, KeyConditionExpression, ExpressionAttributeValues,
              ExclusiveStartKey=None, **kwargs):
        """Supports the one expression shape vault uses:
        'tenant_id = :t AND begins_with(trace_id, :p)' (:p optional).

        Set `page_size` to make the fake paginate like real DynamoDB
        (~1 MB pages): it then returns `LastEvaluatedKey` until exhausted,
        which is what catches single-page reads."""
        if self.fail:
            raise RuntimeError("dynamo unavailable")
        tenant = ExpressionAttributeValues[":t"]
        prefix = ExpressionAttributeValues.get(":p", "")
        matches = [
            item
            for (item_tenant, sort_key), item in sorted(self.items.items())
            if item_tenant == tenant and sort_key.startswith(prefix)
        ]
        if not self.page_size:
            return {"Items": matches}

        start = 0
        if ExclusiveStartKey is not None:
            last = (ExclusiveStartKey["tenant_id"], ExclusiveStartKey["trace_id"])
            for i, item in enumerate(matches):
                if (item["tenant_id"], item["trace_id"]) == last:
                    start = i + 1
                    break
        page = matches[start : start + self.page_size]
        self.query_calls += 1
        result = {"Items": page}
        if start + self.page_size < len(matches):
            tail = page[-1]
            result["LastEvaluatedKey"] = {
                "tenant_id": tail["tenant_id"],
                "trace_id": tail["trace_id"],
            }
        return result

    def dump_all(self) -> str:
        return json.dumps(list(self.items.values()), default=str)


def fake_secret_fetch(secrets: dict[str, dict]):
    """Returns a fetch(arn) callable over {arn: {"tenant_id","key"}}."""

    def fetch(arn: str) -> str:
        return json.dumps(secrets[arn])

    return fetch
