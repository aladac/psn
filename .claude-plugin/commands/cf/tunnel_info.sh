#!/bin/bash
# Get detailed Cloudflare Tunnel information
set -euo pipefail

NAME="${1:?Usage: tunnel_info.sh <name>}"

echo "=== Tunnel Info: $NAME ==="
cloudflared tunnel info "$NAME"

echo ""
echo "=== Tunnel Routes ==="
cloudflared tunnel route ip show "$NAME" 2>/dev/null || echo "No IP routes configured"

if [[ -f ~/.cloudflared/config.yml ]]; then
  echo ""
  echo "=== Local Config (~/.cloudflared/config.yml) ==="
  cat ~/.cloudflared/config.yml
fi
