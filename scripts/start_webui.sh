#!/usr/bin/env bash
set -e

echo "Starting Web UI Servers..."

# Start Backend
echo "Starting Backend..."
source .venv/bin/activate
# Run from root to ensure imports work if needed, or cd
cd webui/backend
python -m uvicorn app.main:app --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Start Frontend
echo "Starting Frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

# Keep alive
wait $BACKEND_PID $FRONTEND_PID
