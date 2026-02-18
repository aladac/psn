#!/bin/bash
# Get Cloudflare Worker details
set -euo pipefail

NAME="${1:?Usage: worker-info.sh <name>}"

echo "=== Worker: $NAME ==="
echo ""
echo "=== Recent Deployments ==="
wrangler deployments list --name "$NAME" 2>/dev/null || echo "No deployments found"

echo ""
echo "To tail live logs: wrangler tail $NAME"
