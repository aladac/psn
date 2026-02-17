#!/bin/bash
# Deploy to Cloudflare Pages
set -euo pipefail

DIRECTORY="${1:?Usage: pages_deploy.sh <directory> <project> [branch]}"
PROJECT="${2:?Missing project name}"
BRANCH="${3:-main}"

if [[ ! -d "$DIRECTORY" ]]; then
  echo "Error: Directory '$DIRECTORY' does not exist"
  exit 1
fi

echo "Deploying $DIRECTORY to Pages project: $PROJECT (branch: $BRANCH)"

wrangler pages deploy "$DIRECTORY" \
  --project-name="$PROJECT" \
  --branch="$BRANCH"
