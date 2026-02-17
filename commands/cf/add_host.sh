#!/bin/bash
# Add DNS record to Cloudflare zone
set -euo pipefail

ZONE="${1:?Usage: add_host.sh <zone> <type> <name> <content> [proxy]}"
TYPE="${2:?Missing record type (A, AAAA, CNAME, TXT, MX)}"
NAME="${3:?Missing record name (subdomain or @)}"
CONTENT="${4:?Missing record content (IP, hostname, or text)}"
PROXY="${5:-true}"

echo "Creating $TYPE record: $NAME.$ZONE -> $CONTENT (proxy: $PROXY)"

flarectl dns create \
  --zone "$ZONE" \
  --type "$TYPE" \
  --name "$NAME" \
  --content "$CONTENT" \
  --proxy="$PROXY"

echo ""
echo "Verifying record..."
flarectl dns list --zone "$ZONE" | grep -i "$NAME" || echo "Record not found in listing"
