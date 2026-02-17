#!/bin/bash
# Create a new Cloudflare Tunnel
set -euo pipefail

NAME="${1:?Usage: add-tunnel.sh <name>}"

echo "Creating tunnel: $NAME"
cloudflared tunnel create "$NAME"

echo ""
echo "Next steps:"
echo "1. Configure ~/.cloudflared/config.yml with ingress rules"
echo "2. Route DNS: cloudflared tunnel route dns $NAME <hostname>"
echo "3. Run tunnel: cloudflared tunnel run $NAME"
