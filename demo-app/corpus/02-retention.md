# Retention

Payloads expire after **7 days**. DynamoDB TTL uses `expires_at`. Lambda
CloudWatch logs also retain 7 days.

Prompts at rest are hashed (`prompt_hash`) plus a masked `prompt_preview`.
Email and SSN must not appear in stored JSON. Fail-closed redaction maps to
`redaction_failed` and stores nothing.
