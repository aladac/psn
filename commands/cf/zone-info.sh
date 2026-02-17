#!/bin/bash
# Get Cloudflare zone details and DNS records
set -euo pipefail

ZONE="${1:?Usage: zone-info.sh <zone>}"

echo "=== Zone Info: $ZONE ==="
flarectl zone info --zone "$ZONE"

echo ""
echo "=== DNS Records ==="
flarectl dns list --zone "$ZONE"
