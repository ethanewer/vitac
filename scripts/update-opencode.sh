#!/usr/bin/env bash
set -euo pipefail

# Update the OpenCode audio SDK and binary from the git submodule.
# Usage: scripts/update-opencode.sh [branch]
#   branch  Git branch to update to (default: dev)

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OC_DIR="$REPO_DIR/opencode-audio"
BRANCH="${1:-dev}"

echo "==> Updating opencode-audio submodule (branch: $BRANCH)"

# Initialise the submodule if it hasn't been cloned yet
git -C "$REPO_DIR" submodule update --init opencode-audio

# Fetch and reset to latest on the requested branch
git -C "$OC_DIR" fetch origin
git -C "$OC_DIR" checkout "$BRANCH"
git -C "$OC_DIR" reset --hard "origin/$BRANCH"

echo "==> Installing dependencies"
bun install --cwd "$OC_DIR"

echo "==> Building opencode (all targets)"
bun run --cwd "$OC_DIR/packages/opencode" build

BINARY="$OC_DIR/packages/opencode/dist/opencode-linux-arm64/bin/opencode"
if [ ! -f "$BINARY" ]; then
  echo "ERROR: Build did not produce $BINARY"
  exit 1
fi

echo "==> Copying linux-arm64 binary to benchmarks/vitac/ts-runner/bin/"
mkdir -p "$REPO_DIR/benchmarks/vitac/ts-runner/bin"
cp "$BINARY" "$REPO_DIR/benchmarks/vitac/ts-runner/bin/opencode-linux-arm64"
chmod +x "$REPO_DIR/benchmarks/vitac/ts-runner/bin/opencode-linux-arm64"

echo "==> Done. Binary:"
ls -lh "$REPO_DIR/benchmarks/vitac/ts-runner/bin/opencode-linux-arm64"
echo "SDK source at: $OC_DIR/packages/sdk/js/src/v2/"
