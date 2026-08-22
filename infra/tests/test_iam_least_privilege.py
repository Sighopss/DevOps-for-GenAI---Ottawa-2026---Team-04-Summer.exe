"""Regression tests for the Terraform IAM wildcard guard."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_iam_least_privilege import find_violations


class IamLeastPrivilegeGuardTests(unittest.TestCase):
    def test_rejects_wildcard_resource_on_allow(self) -> None:
        hcl = '''statement {
          effect = "Allow"
          actions = ["s3:GetObject"]
          resources = ["*"]
        }'''
        self.assertIn("Resource '*'", "\n".join(find_violations(Path("bad.tf"), hcl)))

    def test_rejects_service_wildcard_action_on_allow(self) -> None:
        hcl = '''statement {
          actions = ["dynamodb:*"]
          resources = ["arn:aws:dynamodb:us-east-1:123:table/one"]
        }'''
        self.assertIn("dynamodb:*", "\n".join(find_violations(Path("bad.tf"), hcl)))

    def test_allows_scoped_actions_and_arns(self) -> None:
        hcl = '''statement {
          effect = "Allow"
          actions = ["s3:GetObject", "dynamodb:Query"]
          resources = ["arn:aws:s3:::bucket/tenant-a/*"]
        }'''
        self.assertEqual([], find_violations(Path("good.tf"), hcl))

    def test_allows_wildcards_in_explicit_deny(self) -> None:
        hcl = '''statement {
          effect = "Deny"
          actions = ["s3:*"]
          resources = ["*"]
        }'''
        self.assertEqual([], find_violations(Path("deny.tf"), hcl))


if __name__ == "__main__":
    unittest.main()
