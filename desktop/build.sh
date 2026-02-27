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
STATIC_EXPORT=true npm run build

echo "==> Copying static files to desktop/frontend-dist..."
rm -rf "$DESKTOP_DIR/frontend-dist"
cp -r "$FRONTEND_DIR/out" "$DESKTOP_DIR/frontend-dist"

echo "==> Building Tauri desktop app..."
cd "$DESKTOP_DIR"
npx tauri build

echo "==> Build complete! Installers are in desktop/src-tauri/target/release/bundle/"
