#!/usr/bin/env bash
set -euo pipefail

# CrewHub Desktop Build Script
# Builds the Next.js frontend as a static export, then packages with Tauri.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
FRONTEND_DIR="$ROOT_DIR/frontend"
DESKTOP_DIR="$SCRIPT_DIR"

echo "==> Building frontend static export..."
cd "$FRONTEND_DIR"

# Temporarily exclude files/dirs incompatible with output:"export":
# - middleware.ts uses server-only APIs (cookies, NextResponse.redirect)
# - Dynamic route dirs ([id], [slug]) require generateStaticParams which
#   can't coexist with "use client". These pages are fully client-rendered
#   in the desktop app.
BAK_DIR="$FRONTEND_DIR/.desktop-bak"
mkdir -p "$BAK_DIR"

restore_files() {
  if [[ -d "$BAK_DIR" ]]; then
    # Restore middleware
    [[ -f "$BAK_DIR/middleware.ts" ]] && mv "$BAK_DIR/middleware.ts" "$FRONTEND_DIR/src/middleware.ts"
    # Restore dynamic route dirs
    for marker in "$BAK_DIR"/*.marker; do
      [[ -f "$marker" ]] || continue
      original=$(cat "$marker")
      dirname=$(basename "$marker" .marker)
      [[ -d "$BAK_DIR/$dirname" ]] && mv "$BAK_DIR/$dirname" "$original"
      rm -f "$marker"
    done
    rm -rf "$BAK_DIR"
  fi
}
trap restore_files EXIT

# Move middleware aside
[[ -f "$FRONTEND_DIR/src/middleware.ts" ]] && mv "$FRONTEND_DIR/src/middleware.ts" "$BAK_DIR/middleware.ts"

# Move dynamic route dirs aside
DYNAMIC_ROUTES=(
  "src/app/(marketplace)/agents/[id]"
  "src/app/(marketplace)/categories/[slug]"
  "src/app/(marketplace)/dashboard/tasks/[id]"
  "src/app/admin/agents/[id]"
)
for route in "${DYNAMIC_ROUTES[@]}"; do
  full="$FRONTEND_DIR/$route"
  if [[ -d "$full" ]]; then
    safename=$(echo "$route" | tr '/' '_')
    mv "$full" "$BAK_DIR/$safename"
    echo "$full" > "$BAK_DIR/$safename.marker"
  fi
done

STATIC_EXPORT=true npm run build

# Restore immediately (trap is a safety net)
restore_files

echo "==> Copying static files to desktop/frontend-dist..."
rm -rf "$DESKTOP_DIR/frontend-dist"
cp -r "$FRONTEND_DIR/out" "$DESKTOP_DIR/frontend-dist"

echo "==> Installing desktop dependencies..."
cd "$DESKTOP_DIR"
npm install

echo "==> Building Tauri desktop app..."
npx tauri build

echo "==> Build complete! Installers are in desktop/src-tauri/target/release/bundle/"
