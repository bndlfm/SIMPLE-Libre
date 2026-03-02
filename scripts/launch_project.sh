#!/usr/bin/env bash

# Get the project root directory
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)"
cd "$repo_root"

# Activate venv if it exists
if [ -f "$repo_root/.venv/bin/activate" ]; then
    source "$repo_root/.venv/bin/activate"
    echo "✓ venv activated"
else
    echo "⚠ No .venv found. Please run 'python -m venv .venv' first."
    exit 1
fi

# Set PYTHONPATH to include app directory
export PYTHONPATH="$repo_root/app:$repo_root/app/environments"
echo "PYTHONPATH set to $PYTHONPATH"

# Function to kill processes on exit
cleanup() {
    echo "Stopping servers..."
    if [ -n "$backend_pid" ]; then
        kill $backend_pid 2>/dev/null
    fi
    if [ -n "$frontend_pid" ]; then
        kill $frontend_pid 2>/dev/null
    fi
}
trap cleanup EXIT

# Start Backend
echo "Starting Backend (Uvicorn)..."
python -m uvicorn webui.backend.app.main:app --host 127.0.0.1 --port 8001 --reload &
backend_pid=$!
echo "Backend running on PID $backend_pid"

# Start Frontend
echo "Starting Frontend (Vite)..."
cd webui/frontend
npm run dev -- --host 127.0.0.1 --port 5173 &
frontend_pid=$!
cd ../..
echo "Frontend running on PID $frontend_pid"

echo "---------------------------------------------------"
echo "SIMPLE-Libre WebUI is launching..."
echo "Backend:  http://127.0.0.1:8001"
echo "Frontend: http://127.0.0.1:5173"
echo "---------------------------------------------------"
echo "Press Ctrl+C to stop everything."

# Wait forever
wait
