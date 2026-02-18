#!/bin/bash
# List installed Claude Code plugins
set -euo pipefail

unset CLAUDECODE && claude plugin list
