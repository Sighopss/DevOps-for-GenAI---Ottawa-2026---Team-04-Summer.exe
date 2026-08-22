#!/usr/bin/env python3
"""Remove Cursor co-author / marketing trailers from a commit message file."""

from __future__ import annotations

import sys

BANNED = (
    "co-authored-by: cursor",
    "cursoragent@cursor.com",
    "made-with: cursor",
    "made with cursor",
)


def strip_message(text: str) -> str:
    kept = [
        line
        for line in text.splitlines()
        if not any(token in line.lower() for token in BANNED)
    ]
    if not kept:
        return text
    return "\n".join(kept).rstrip() + "\n"


def main() -> None:
    path = sys.argv[1]
    original = open(path, encoding="utf-8").read()
    cleaned = strip_message(original)
    open(path, "w", encoding="utf-8").write(cleaned)


if __name__ == "__main__":
    main()
