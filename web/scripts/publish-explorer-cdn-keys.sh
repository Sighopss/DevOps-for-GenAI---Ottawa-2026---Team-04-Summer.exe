#!/usr/bin/env bash
# CloudFront + S3 REST (OAC) does not resolve /explorer/ → explorer/index.html.
# After `aws s3 sync out/ … --delete`, re-put directory-index shims so hard
# navigations to /explorer and /explorer/ serve the explorer instead of the
# SPA custom-error remap to welcome index.html.
set -euo pipefail

BUCKET="${1:?usage: publish-explorer-cdn-keys.sh <bucket> [distribution-id]}"
DIST="${2:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INDEX="${ROOT}/out/explorer/index.html"

if [[ ! -f "${INDEX}" ]]; then
  echo "missing ${INDEX}; run pnpm build first" >&2
  exit 1
fi

aws s3api put-object \
  --bucket "${BUCKET}" \
  --key explorer \
  --body "${INDEX}" \
  --content-type text/html \
  --cache-control "public, max-age=60" >/dev/null

aws s3api put-object \
  --bucket "${BUCKET}" \
  --key "explorer/" \
  --body "${INDEX}" \
  --content-type text/html \
  --cache-control "public, max-age=60" >/dev/null

if [[ -n "${DIST}" ]]; then
  aws cloudfront create-invalidation \
    --distribution-id "${DIST}" \
    --paths "/explorer" "/explorer/" "/explorer/index.html" "/*" >/dev/null
fi

echo "published explorer CDN keys on s3://${BUCKET}"
