#!/usr/bin/env bash
set -euo pipefail

# Release script for choo
# Usage: ./scripts/release.sh [patch|minor|major]
#   Defaults to patch if no argument given.

BUMP="${1:-patch}"

echo "=== choo release ==="
echo ""

# 1. Check clean working tree
if [[ -n "$(git status --porcelain)" ]]; then
    echo "✗ Working tree is dirty. Commit or stash changes first."
    exit 1
fi

# 2. Run tests
echo "Running tests..."
if ! uv run --group test pytest --ignore=tests/test_sdk_integration.py -q; then
    echo "✗ Tests failed. Fix before releasing."
    exit 1
fi
echo ""

# 3. Bump version
echo "Bumping version ($BUMP)..."
uv version --bump "$BUMP"
NEW_VERSION=$(uv version --short)
echo "New version: $NEW_VERSION"
echo ""

# 4. Commit version bump
git add pyproject.toml uv.lock
git commit -m "release: v$NEW_VERSION"

# 5. Push
BRANCH=$(git branch --show-current)
echo "Pushing $BRANCH..."
git push origin "$BRANCH"
echo ""

# 6. Create GitHub release (triggers publish workflow)
TAG="v$NEW_VERSION"
echo "Creating release $TAG..."
gh release create "$TAG" \
    --target "$BRANCH" \
    --title "$TAG" \
    --generate-notes

echo ""
echo "✓ Released $TAG"
echo "  PyPI publish will be triggered by GitHub Actions."
echo "  Watch: gh run list --workflow=publish.yml --limit 1"
