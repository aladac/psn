#!/bin/bash
# Install a Claude Code plugin from marketplace
set -euo pipefail

if [ -z "${1:-}" ]; then
    echo "Error: Plugin name required"
    echo "Usage: /claude:plugins:install <plugin>"
    exit 1
fi

unset CLAUDECODE && claude plugin install "$1"
