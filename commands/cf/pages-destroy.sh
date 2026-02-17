#!/bin/bash
# Delete a Cloudflare Pages project
set -euo pipefail

PROJECT="${1:?Usage: pages-destroy.sh <project>}"

echo "Deleting Pages project: $PROJECT"
echo "Warning: This deletes all deployments and custom domains."
read -p "Are you sure? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  wrangler pages project delete "$PROJECT" --yes
  echo "Project deleted."
else
  echo "Aborted."
  exit 1
fi
