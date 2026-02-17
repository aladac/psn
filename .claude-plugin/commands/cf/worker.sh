#!/bin/bash
# Cloudflare Worker operations
set -euo pipefail

ACTION="${1:?Usage: worker.sh <action> [name]}"
NAME="${2:-}"

case "$ACTION" in
  deploy)
    echo "Deploying worker..."
    wrangler deploy
    ;;
  dev)
    echo "Starting dev server..."
    wrangler dev
    ;;
  tail)
    [[ -z "$NAME" ]] && { echo "Error: worker name required for tail"; exit 1; }
    echo "Tailing logs for $NAME..."
    wrangler tail "$NAME"
    ;;
  delete)
    [[ -z "$NAME" ]] && { echo "Error: worker name required for delete"; exit 1; }
    echo "Deleting worker: $NAME"
    read -p "Are you sure? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      wrangler delete "$NAME"
    else
      echo "Aborted."
      exit 1
    fi
    ;;
  init)
    [[ -z "$NAME" ]] && { echo "Error: worker name required for init"; exit 1; }
    echo "Initializing worker: $NAME"
    wrangler init "$NAME"
    ;;
  *)
    echo "Unknown action: $ACTION"
    echo "Actions: deploy, dev, tail, delete, init"
    exit 1
    ;;
esac
