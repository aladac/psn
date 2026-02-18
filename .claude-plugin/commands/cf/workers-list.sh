#!/bin/bash
# List Cloudflare Workers
set -euo pipefail

echo "=== Cloudflare Workers ==="
wrangler deployments list 2>/dev/null || wrangler whoami
