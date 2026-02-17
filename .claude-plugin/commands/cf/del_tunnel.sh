#!/bin/bash
# Delete a Cloudflare Tunnel
set -euo pipefail

NAME="${1:?Usage: del_tunnel.sh <name>}"

echo "Deleting tunnel: $NAME"
echo "Warning: Ensure tunnel is stopped and DNS routes are removed."
read -p "Are you sure? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  cloudflared tunnel delete "$NAME"
  echo "Tunnel deleted."
else
  echo "Aborted."
  exit 1
fi
