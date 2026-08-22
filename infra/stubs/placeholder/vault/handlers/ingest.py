"""Placeholder ingest handler. Alexis replaces this by shipping vault/."""

import json


def handler(event, context):
    return {
        "statusCode": 501,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(
            {
                "error": {
                    "code": "invalid",
                    "message": "vault handlers not packaged",
                }
            }
        ),
    }
