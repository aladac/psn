#!/bin/bash
# Delete DNS record from Cloudflare zone
set -euo pipefail

ZONE="${1:?Usage: del-host.sh <zone> <record-id>}"
RECORD_ID="${2:?Missing record ID (get from zone-info.sh)}"

echo "Deleting record $RECORD_ID from zone $ZONE"
read -p "Are you sure? [y/N] " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  flarectl dns delete --zone "$ZONE" --id "$RECORD_ID"
  echo "Record deleted."
else
  echo "Aborted."
  exit 1
fi
