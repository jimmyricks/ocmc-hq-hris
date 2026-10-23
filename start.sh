#!/usr/bin/env bash
set -e

# Resolve the directory this script lives in, so it works from anywhere.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# API URL used by the Vite dev server proxy and any frontend runtime fetch
export API_URL="${API_URL:-http://localhost:8005}"

# Backend settings
export PORT="${PORT:-8005}"
export HOST="${HOST:-0.0.0.0}"

echo "Starting backend on http://$HOST:$PORT"
echo "Starting frontend dev server on http://localhost:5173"
echo "API proxy target: $API_URL"
echo "Press Ctrl-C to stop both servers"
echo ""

# Start backend in the background.
cd backend

# Bootstrap the venv if it doesn't exist yet.
if [ ! -x .venv/bin/python ]; then
    echo "Creating backend virtualenv..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

# Use the venv's interpreter directly; `source activate` can silently pick up
# a foreign venv if the script was copied from another project.
.venv/bin/python -m uvicorn app.main:app --host "$HOST" --port "$PORT" --reload &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# Ensure the backend is terminated when this script exits.
cleanup() {
    echo ""
    echo "Stopping backend (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Wait a moment for the backend to bind before starting the frontend.
sleep 1

# Start frontend in the foreground.
cd frontend
pnpm run dev -- --host 0.0.0.0 --port 5173
