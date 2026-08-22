"""Keep documented abuse and capacity limits wired into source."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8-sig")


def _default(variable: str, text: str) -> str:
    match = re.search(
        rf'variable\s+"{re.escape(variable)}"\s*\{{.*?\bdefault\s*=\s*([^\s]+)',
        text,
        re.DOTALL,
    )
    if not match:
        raise AssertionError(f"missing default for {variable}")
    return match.group(1).strip()


class CapacityControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.variables = _text("infra/variables.tf")

    def test_api_limits_are_bounded_and_wired(self) -> None:
        self.assertEqual("10", _default("api_throttle_rate", self.variables))
        self.assertEqual("20", _default("api_throttle_burst", self.variables))
        api = _text("infra/api.tf")
        self.assertIn("throttling_rate_limit  = var.api_throttle_rate", api)
        self.assertIn("throttling_burst_limit = var.api_throttle_burst", api)

    def test_lambda_limits_are_bounded_and_wired(self) -> None:
        self.assertEqual("30", _default("lambda_timeout_seconds", self.variables))
        self.assertEqual("512", _default("lambda_memory_mb", self.variables))
        self.assertEqual("-1", _default("lambda_reserved_concurrency", self.variables))
        lambda_tf = _text("infra/lambda.tf")
        self.assertEqual(2, lambda_tf.count("reserved_concurrent_executions = var.lambda_reserved_concurrency"))

    def test_agent_budget_is_bounded(self) -> None:
        main = _text("demo-app/src/demo_app/main.py")
        bedrock = _text("demo-app/src/demo_app/bedrock.py")
        self.assertRegex(main, r"MAX_AGENT_ITERATIONS\s*=\s*1\b")
        self.assertRegex(bedrock, r"MAX_OUTPUT_TOKENS\s*=\s*256\b")
        self.assertRegex(bedrock, r"CONNECT_TIMEOUT_S\s*=\s*5\b")
        self.assertRegex(bedrock, r"READ_TIMEOUT_S\s*=\s*30\b")
        self.assertIn('retries={"max_attempts": 1}', bedrock)
        self.assertIn('"maxTokens": MAX_OUTPUT_TOKENS', bedrock)

    def test_agreed_bedrock_models_are_allowlisted(self) -> None:
        required = (
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "amazon.nova-lite-v1:0",
            "amazon.titan-embed-text-v2:0",
        )
        for relative in (
            "infra/variables.tf",
            "infra/envs/dev.tfvars.example",
            "infra/envs/prod.tfvars.example",
        ):
            text = _text(relative)
            for model_id in required:
                self.assertIn(model_id, text, msg=relative)
        bedrock = _text("demo-app/src/demo_app/bedrock.py")
        self.assertIn('DEFAULT_CONVERSE_MODEL_ID = "amazon.nova-lite-v1:0"', bedrock)
        self.assertIn('DEFAULT_EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"', bedrock)

    def test_limit_behavior_is_documented(self) -> None:
        scale = _text("docs/SCALE.md")
        for evidence in ("100 flights/minute", "429 Too Many Requests", "30 seconds", "< $0.01"):
            self.assertIn(evidence, scale)


if __name__ == "__main__":
    unittest.main()
