#!/bin/bash
# Update Claude Code marketplace plugin manifests
set -euo pipefail

if [ -n "${1:-}" ]; then
    unset CLAUDECODE && claude plugin marketplace update "$1"
else
    unset CLAUDECODE && claude plugin marketplace update
fi
