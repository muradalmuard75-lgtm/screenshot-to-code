#!/bin/bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "============================================"
echo " Starting Screenshot-to-Code Application "
echo "============================================"

# 1. Start Backend on Port 7001
cd "$DIR/backend"
if [ ! -f ".env" ]; then
  cat << 'EOF' > .env
# Enter your free Gemini API key or OpenAI key below:
GEMINI_API_KEY=
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
EOF
fi

echo "Starting Backend on http://127.0.0.1:7001..."
"$DIR/backend/.venv/bin/uvicorn" main:app --host 127.0.0.1 --port 7001 &
BACKEND_PID=$!

cleanup() {
  echo ""
  echo "Shutting down Screenshot-to-Code..."
  kill $BACKEND_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 2. Start Frontend Dev Server on Port 5173
echo "Starting Frontend on http://0.0.0.0:5173..."
cd "$DIR/frontend"
/home/ubuntu/.local/share/pnpm/bin/pnpm run dev --host 0.0.0.0 --port 5173
