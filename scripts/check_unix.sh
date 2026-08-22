#!/usr/bin/env bash
set -euo pipefail
for cmd in grep sed awk; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "missing ${cmd}" >&2
    exit 1
  }
done
echo ok
