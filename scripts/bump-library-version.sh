#!/usr/bin/env bash
# Auto-bump patch version in pyproject.toml on every code commit.
set -e

PYPROJECT="pyproject.toml"

# Extract current version (e.g. "0.1.1")
current=$(grep '^version = ' "$PYPROJECT" | head -1 | sed 's/version = "\(.*\)"/\1/')
if [ -z "$current" ]; then
  echo "bump-library-version: could not find version in $PYPROJECT" >&2
  exit 1
fi

major=$(echo "$current" | cut -d. -f1)
minor=$(echo "$current" | cut -d. -f2)
patch=$(echo "$current" | cut -d. -f3)

new_patch=$((patch + 1))
new_version="${major}.${minor}.${new_patch}"

# Replace version in pyproject.toml
sed -i '' "s/^version = \"${current}\"/version = \"${new_version}\"/" "$PYPROJECT" 2>/dev/null \
  || sed -i "s/^version = \"${current}\"/version = \"${new_version}\"/" "$PYPROJECT"

# Stage the updated pyproject.toml
git add "$PYPROJECT"

echo "bump-library-version: ${current} → ${new_version}"
