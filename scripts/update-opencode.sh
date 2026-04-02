#!/usr/bin/env bash
set -euo pipefail

# Update the OpenCode audio SDK and binary from GitHub.
# Usage: scripts/update-opencode.sh [branch]
#   branch  Git branch to pull (default: dev)

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OC_DIR="$REPO_DIR/opencode-audio"
BRANCH="${1:-dev}"
REMOTE="git@github.com:ethanewer/opencode-audio.git"

echo "==> Updating opencode-audio (branch: $BRANCH)"

if [ -d "$OC_DIR/.git" ]; then
  echo "Pulling latest changes..."
  git -C "$OC_DIR" fetch origin
  git -C "$OC_DIR" checkout "$BRANCH"
  git -C "$OC_DIR" reset --hard "origin/$BRANCH"
else
  echo "Cloning $REMOTE ..."
  git clone --branch "$BRANCH" --single-branch "$REMOTE" "$OC_DIR"
fi

echo "==> Installing dependencies"
bun install --cwd "$OC_DIR"

echo "==> Building opencode (all targets)"
bun run --cwd "$OC_DIR/packages/opencode" build

BINARY="$OC_DIR/packages/opencode/dist/opencode-linux-arm64/bin/opencode"
if [ ! -f "$BINARY" ]; then
  echo "ERROR: Build did not produce $BINARY"
  exit 1
fi

echo "==> Copying linux-arm64 binary to ts-runner/bin/"
mkdir -p "$REPO_DIR/ts-runner/bin"
cp "$BINARY" "$REPO_DIR/ts-runner/bin/opencode-linux-arm64"
chmod +x "$REPO_DIR/ts-runner/bin/opencode-linux-arm64"

echo "==> Done. Binary:"
ls -lh "$REPO_DIR/ts-runner/bin/opencode-linux-arm64"
echo "SDK source at: $OC_DIR/packages/sdk/js/src/v2/"
