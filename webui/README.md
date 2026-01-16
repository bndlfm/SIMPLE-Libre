# SIMPLE Web UI (Cuba Libre)

This directory contains an initial Web UI plan and a runnable prototype skeleton for the SIMPLE framework, focused first on the Cuba Libre environment.

Goals:
- Interactive board map (clickable spaces / targets)
- Visualize pieces, markers, control, and derived tracks
- Show current/next card and deck status
- Show available forces / pools
- Support:
  - Human play vs model
  - Spectator mode during training (stream state updates)

## Structure
- `backend/`: FastAPI server exposing the environment over HTTP/WebSocket
- `frontend/`: React UI (Vite) consuming backend APIs
- `docs/`: UI/UX + architecture + state schema notes

## Run (prototype)

### Backend
1. Create a venv (recommended).
2. Install deps:
   - `pip install -r webui/backend/requirements.txt`
3. Start server:
   - `python -m uvicorn webui.backend.app.main:app --reload --port 8000`

### Frontend
1. `cd webui/frontend`
2. `npm install`
3. `npm run dev`

Open:
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000` (see `/docs` for Swagger)
