#!/bin/bash
# List all Cloudflare Tunnels
set -euo pipefail

cloudflared tunnel list
