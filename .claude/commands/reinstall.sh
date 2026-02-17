#!/bin/bash
# PSN Reinstall Script
# Updates version, reinstalls via uv, syncs plugin and marketplace
set -euo pipefail

PSN_ROOT="/Users/chi/Projects/psn"
MARKETPLACE="/Users/chi/.claude/plugins/marketplaces/saiden"

cd "$PSN_ROOT"

# Get base version (strip any existing +hash suffix)
CURRENT_VERSION=$(sed -n 's/^__version__ = "\([^"]*\)"/\1/p' src/personality/__init__.py)
BASE_VERSION=$(echo "$CURRENT_VERSION" | sed 's/+.*//')

# Get the LAST commit hash BEFORE we make any changes
LAST_HASH=$(git rev-parse --short HEAD)

# New version with hash
NEW_VERSION="${BASE_VERSION}+${LAST_HASH}"

echo "=== PSN Reinstall ==="
echo "Base version: $BASE_VERSION"
echo "Last commit:  $LAST_HASH"
echo "New version:  $NEW_VERSION"
echo ""

# Check if version already matches (avoid loop)
if [[ "$CURRENT_VERSION" == "$NEW_VERSION" ]]; then
    echo "Version already at $NEW_VERSION, skipping version bump"
else
    echo "Updating version to $NEW_VERSION..."

    # Update src/personality/__init__.py
    sed -i '' "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" src/personality/__init__.py

    # Update .claude-plugin/plugin.json
    sed -i '' "s/\"version\": \".*\"/\"version\": \"$NEW_VERSION\"/" .claude-plugin/plugin.json

    echo "Version updated in:"
    echo "  - src/personality/__init__.py"
    echo "  - .claude-plugin/plugin.json"

    # Commit version change if there are changes
    if ! git diff --quiet; then
        echo ""
        echo "Committing version update..."
        git add src/personality/__init__.py .claude-plugin/plugin.json
        git commit -m "Version $NEW_VERSION"
        echo "Committed."
    fi
fi

# Push if ahead of remote
if git status | grep -q "Your branch is ahead"; then
    echo ""
    echo "Pushing to remote..."
    git push
fi

echo ""
echo "=== Reinstall via uv ==="
cd "$PSN_ROOT"
uv pip install --system --break-system-packages -e .

echo ""
echo "=== Verify Installation ==="
psn --version

echo ""
echo "=== Update Plugin (local) ==="
cd "$PSN_ROOT"
git pull --rebase 2>/dev/null || echo "Already up to date"

echo ""
echo "=== Update Marketplace ==="
cd "$MARKETPLACE"
git fetch origin
git pull --rebase origin main 2>/dev/null || echo "Already up to date"

# Update submodules (psn, browse)
git submodule update --remote --merge
echo "Marketplace updated."

echo ""
echo "=== Done ==="
echo "Version: $NEW_VERSION"
echo "Restart Claude CLI to load updated plugin."
