#!/usr/bin/env bash
set -euo pipefail

# Rebuild the original Vite frontend from the exact immutable commit that
# produced the preserved interface. We copy only frontend files; the current
# FastAPI backend in app/ is never replaced by this process.
SOURCE_REF="agent/substituir-sistema-operacional"
SOURCE_SHA="20e92f6ecea51b8ae0afba88391ae03e53e68e93"
WORK_DIR=".agent-web-source"

rm -rf "$WORK_DIR" dist
mkdir -p "$WORK_DIR"

git fetch --quiet --depth=1 origin "$SOURCE_REF"
ACTUAL_SHA="$(git rev-parse FETCH_HEAD)"
if [[ "$ACTUAL_SHA" != "$SOURCE_SHA" ]]; then
  echo "Refusing to build: protected frontend source moved ($ACTUAL_SHA != $SOURCE_SHA)" >&2
  exit 1
fi

git archive FETCH_HEAD \
  index.html package.json package-lock.json \
  tsconfig.json tsconfig.node.json vite.config.ts \
  tailwind.config.ts postcss.config.cjs src \
  | tar -x -C "$WORK_DIR"

python scripts/patch-agent-frontend.py "$WORK_DIR/src/App.tsx"

pushd "$WORK_DIR" >/dev/null
npm ci --no-audit --no-fund
VITE_SEO_API_URL=/seo-api npm run build
popd >/dev/null

mv "$WORK_DIR/dist" dist
rm -rf "$WORK_DIR"

echo "Agent-enabled frontend built from protected source $SOURCE_SHA"
