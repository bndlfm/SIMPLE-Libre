#!/usr/bin/env fish

# Get the project root directory
set repo_root (realpath (dirname (status filename))/..)
cd $repo_root

# Activate venv if it exists
if test -f "$repo_root/.venv/bin/activate.fish"
    source "$repo_root/.venv/bin/activate.fish"
    echo "✓ venv activated"
else
    echo "⚠ No .venv found. Please run 'python -m venv .venv' first."
    exit 1
end

# Set PYTHONPATH to include app directory
set -gx PYTHONPATH "$repo_root/app:$repo_root/app/environments"
echo "PYTHONPATH set to $PYTHONPATH"

# Function to kill processes on exit
function cleanup
    echo "Stopping servers..."
    if test -n "$backend_pid"
        kill $backend_pid 2>/dev/null
    end
    if test -n "$frontend_pid"
        kill $frontend_pid 2>/dev/null
    end
end
trap cleanup EXIT

# Start Backend
echo "Starting Backend (Uvicorn)..."
python -m uvicorn webui.backend.app.main:app --host 127.0.0.1 --port 8001 --reload &
set backend_pid $last_pid
echo "Backend running on PID $backend_pid"

# Start Frontend
echo "Starting Frontend (Vite)..."
cd webui/frontend
npm run dev -- --host 127.0.0.1 --port 5173 &
set frontend_pid $last_pid
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
