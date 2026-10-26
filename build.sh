#!/usr/bin/env bash
set -e

echo "=== Building Screenshot to Code for Production ==="

# 1. Install frontend deps and build static bundle
cd frontend
if ! command -v pnpm &> /dev/null; then
    npm install -g pnpm
fi
pnpm install
pnpm run build
cd ..

# 2. Install backend python deps
cd backend
pip install -r requirements.txt
cd ..

echo "=== Build Complete ==="
