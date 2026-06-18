#!/usr/bin/env bash
# Build anything-analyzer Docker image and push to GHCR
# Output: nothing downloaded — use ghcr.io/callacat/gha-build-farm/anything-analyzer:latest
set -euo pipefail

VERSION="${1:-latest}"
echo "Building anything-analyzer Docker image (version=${VERSION})..."

# Assume GHCR login already done in workflow YAML step
# Clone and build
git clone --depth 1 https://github.com/Mouseww/anything-analyzer.git /tmp/anything-analyzer

docker buildx build \
  --platform linux/amd64 \
  -t "ghcr.io/callacat/gha-build-farm/anything-analyzer:${VERSION}" \
  -t "ghcr.io/callacat/gha-build-farm/anything-analyzer:latest" \
  --push \
  /tmp/anything-analyzer

echo "✅ anything-analyzer Docker image pushed: ghcr.io/callacat/gha-build-farm/anything-analyzer:${VERSION}"
echo "/tmp/build-output" > /tmp/build-artifact-dir.txt
