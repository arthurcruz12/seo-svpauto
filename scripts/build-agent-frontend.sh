#!/usr/bin/env bash
set -euo pipefail

# Rebuild the original Vite frontend from the exact immutable commit that
# produced the preserved interface. We copy only frontend files; the current
# FastAPI backend in app/ is never replaced by this process.
SOURCE_SHA="20e92f6ecea51b8ae0afba88391ae03e53e68e93"
WORK_DIR=".agent-web-source"
ARCHIVE_DIR=".agent-web-archive"
ARCHIVE_FILE="/tmp/seo-protected-frontend.tar.gz"

rm -rf "$WORK_DIR" "$ARCHIVE_DIR" dist
mkdir -p "$WORK_DIR" "$ARCHIVE_DIR"

curl --fail --silent --show-error --location \
  "https://codeload.github.com/arthurcruz12/seo-svpauto/tar.gz/${SOURCE_SHA}" \
  --output "$ARCHIVE_FILE"

tar -xzf "$ARCHIVE_FILE" -C "$ARCHIVE_DIR"
SOURCE_DIR="$(find "$ARCHIVE_DIR" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
if [[ -z "$SOURCE_DIR" || ! -f "$SOURCE_DIR/src/App.tsx" ]]; then
  echo "Protected frontend source archive is incomplete" >&2
  exit 1
fi

cp "$SOURCE_DIR/index.html" "$WORK_DIR/index.html"
cp "$SOURCE_DIR/package.json" "$WORK_DIR/package.json"
cp "$SOURCE_DIR/package-lock.json" "$WORK_DIR/package-lock.json"
cp "$SOURCE_DIR/tsconfig.json" "$WORK_DIR/tsconfig.json"
cp "$SOURCE_DIR/tsconfig.node.json" "$WORK_DIR/tsconfig.node.json"
cp "$SOURCE_DIR/vite.config.ts" "$WORK_DIR/vite.config.ts"
cp "$SOURCE_DIR/tailwind.config.ts" "$WORK_DIR/tailwind.config.ts"
cp "$SOURCE_DIR/postcss.config.cjs" "$WORK_DIR/postcss.config.cjs"
cp -R "$SOURCE_DIR/src" "$WORK_DIR/src"

python scripts/patch-agent-frontend.py "$WORK_DIR/src/App.tsx"
python scripts/patch-work-tasks-ui.py "$WORK_DIR/src/App.tsx"
python scripts/patch-work-execution-ui.py "$WORK_DIR/src/App.tsx"
python scripts/patch-work-preview-bridge.py "$WORK_DIR/src/App.tsx"
python scripts/patch-work-cloud-sync.py "$WORK_DIR/src/App.tsx"
python scripts/patch-work-traceability-ui.py "$WORK_DIR/src/App.tsx"
python scripts/patch-cloud-trash-ui.py "$WORK_DIR/src/App.tsx"
python scripts/patch-agent-vercel-bridge.py "$WORK_DIR/src/App.tsx"

pushd "$WORK_DIR" >/dev/null
npm ci --no-audit --no-fund
VITE_SEO_API_URL=/seo-api npm run build
popd >/dev/null

mv "$WORK_DIR/dist" dist
rm -rf "$WORK_DIR" "$ARCHIVE_DIR" "$ARCHIVE_FILE"

echo "Agent-enabled frontend built from protected source $SOURCE_SHA"
