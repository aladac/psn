#!/bin/bash
# List Cloudflare Pages projects
set -euo pipefail

wrangler pages project list
