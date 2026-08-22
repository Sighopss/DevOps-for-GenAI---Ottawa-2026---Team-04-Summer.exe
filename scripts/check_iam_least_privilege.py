"""Fail CI when an authored Allow statement gains wildcard IAM scope.

This deliberately checks Terraform identity-policy source rather than an applied
account so it runs on every pull request without AWS credentials. KMS and bucket
resource policies have different wildcard semantics and are reviewed separately.
Explicit Deny statements may use wildcards; their purpose is to reduce privilege.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_ASSIGNMENT = re.compile(r"\b(actions|resources)\s*=\s*\[(.*?)\]", re.DOTALL)
_QUOTED = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
_STATEMENT = re.compile(r"\bstatement\s*\{")
_EFFECT_DENY = re.compile(r'\beffect\s*=\s*"Deny"')
_SERVICE_WILDCARD = re.compile(r"^[a-z0-9-]+:\*$", re.IGNORECASE)


def _statement_blocks(text: str) -> list[str]:
    """Return balanced HCL statement blocks; enough for policy-source linting."""
    blocks: list[str] = []
    for match in _STATEMENT.finditer(text):
        depth = 0
        in_string = False
        escaped = False
        for index in range(match.end() - 1, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    blocks.append(text[match.start() : index + 1])
                    break
    return blocks


def find_violations(path: Path, text: str) -> list[str]:
    violations: list[str] = []
    for block_number, block in enumerate(_statement_blocks(text), start=1):
        if _EFFECT_DENY.search(block):
            continue
        for field, raw_values in _ASSIGNMENT.findall(block):
            for value in _QUOTED.findall(raw_values):
                if field == "resources" and value == "*":
                    violations.append(
                        f"{path}: Allow statement {block_number} grants Resource '*'"
                    )
                if field == "actions" and (
                    value == "*" or _SERVICE_WILDCARD.fullmatch(value)
                ):
                    violations.append(
                        f"{path}: Allow statement {block_number} grants Action {value!r}"
                    )
    return violations


def check(paths: list[Path]) -> list[str]:
    violations: list[str] = []
    for path in paths:
        violations.extend(find_violations(path, path.read_text(encoding="utf-8-sig")))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    violations = check(args.paths)
    if violations:
        print("IAM least-privilege guard failed:")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print(f"ok: {len(args.paths)} Terraform files contain no wildcard Allow grants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
