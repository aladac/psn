#!/bin/bash
# Update installed Claude Code plugins
set -euo pipefail

if [ -n "${1:-}" ]; then
    unset CLAUDECODE && claude plugin update "$1"
else
    echo "Listing installed plugins..."
    unset CLAUDECODE && claude plugin list
    echo ""
    echo "To update a specific plugin, run: /claude:plugins:update <plugin-name>"
fi
