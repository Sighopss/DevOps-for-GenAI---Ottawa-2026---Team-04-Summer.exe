#!/usr/bin/env bash
# One-time rewrite of git history to drop Cursor co-author trailers.
# Requires temporary allow-force-push on main (GitHub branch protection).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Working tree must be clean before rewriting history." >&2
  exit 1
fi

export FILTER_BRANCH_SQUELCH_WARNING=1

git filter-branch -f --msg-filter '
  grep -viE "co-authored-by: cursor|cursoragent@cursor\.com|made-with: cursor|made with cursor" || true
' -- --all

echo ""
echo "Review: git log -5 --format=%B"
echo "Then: git push --force-with-lease origin main"
echo "Re-enable branch protection (no force-push) after push."
