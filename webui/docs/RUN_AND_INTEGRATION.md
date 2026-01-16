# Run + Integration Notes

## 1) Local dev run

### Backend
From repo root:

- Install deps:
  - `pip install -r webui/backend/requirements.txt`
  - Needs `stable-baselines3`, `torch`, and SIMPLE framework deps.

- Run:
  - `python -m uvicorn webui.backend.app.main:app --reload --port 8000`

Endpoints:
- `GET /health`
- `POST /reset` with optional `{ "faction_roles": {"0":"human","1":"ai","2":"ai","3":"ai"} }`
- `GET /state`
- `GET /legal_actions`
- `POST /step` with `{ "action": <int> }` — auto-advances AI turns after human step
- `POST /faction_roles` with `{ "faction_roles": {"0":"human","1":"ai",...} }` — set who is human/AI
- `GET /faction_roles`
- `POST /model/load` with `{ "path": "zoo/cubalibre/best_model.zip", "device": "cpu", "algo": "PPO" }`
- `POST /model/unload`
- `GET /model/info`
- `POST /spectator/start` with `{ "tick_ms": 500, "deterministic": false, "auto_reset": true }`
- `POST /spectator/stop`
- `POST /spectator/speed` with query `?tick_ms=300`
- `GET /spectator/status`
- `POST /training/watch` with `{ "path": "logs/train.jsonl", "poll_seconds": 1 }`
- `GET /training/status`
- `WS /ws` (broadcasts state after each reset/step/spectator tick)

Notes:
- Uses SIMPLE framework Agent class (`app/utils/agents.py`) for AI action selection.
- Model endpoints require `stable-baselines3` (SB3) + PyTorch.
- AI factions auto-advance after each human step — no manual "autoplay" needed.
- Spectator mode runs all-AI games with per-step board updates at configurable speed.
- Training watch expects a JSONL file with one JSON object per line (latest line is broadcast).

### Frontend
From repo root:

- `cd webui/frontend`
- `npm install`
- `npm run dev`

Open:
- `http://localhost:5173`

## 2) What the UI currently supports

- Renders current state snapshot:
  - spaces list with piece counts, terror/sabotage, cash by owner, control
  - tracks (Aid/US Alliance + derived victory markers)
  - current card text + next card peek
  - legal actions (as sparse indices)
- Lets you:
  - `Reset` with faction role configuration (any combo of human/AI for 4 factions)
  - Play as human: submit actions via phase-aware controls, AI auto-responds
  - Load an SB3 PPO model (or use random legal actions as fallback)
  - Spectator mode: watch AI-vs-AI games play out on the board
  - Watch training JSONL metrics
  - Any combination: 1h/3ai, 2h/2ai, 3h/1ai, 4h/0ai, 0h/4ai

## 3) Next steps toward a real board UI

### 3.1 SVG map
- Replace the “space grid” with an SVG that has 13 clickable hit areas.
- Maintain a `spaceId -> {x,y}` layout table.
- Render overlays:
  - piece stacks (counts)
  - terror/sabotage icons
  - control highlight
  - cash markers

### 3.2 Phase-driven UI controls
The env is phase-based (see `PHASE_*` in `app/environments/cubalibre/envs/env.py`).

Plan:
- Instead of a raw numeric action box, show context-aware controls.
- Examples:
  - `PHASE_CHOOSE_MAIN`: show Pass / Event / Ops buttons
  - `PHASE_CHOOSE_EVENT_SIDE`: show Unshaded/Shaded, disable blank side
  - `PHASE_CHOOSE_TARGET_SPACE`: make spaces clickable and translate selection to the target-space action range

### 3.3 Pieces and marker details
- Current serialization returns `pieces_raw` (11-slot vector).
- Next UI iterations should decode those into named counts:
  - Govt: Troops, Police
  - M26: Underground, Active, Base
  - DR: Underground, Active, Base
  - Syn: Underground, Active, Casino(Open), plus `closed_casinos`

## 4) Training spectator mode

Two modes for observing AI play:

### Spectator mode (built-in)
- `POST /spectator/start` runs an all-AI game, broadcasting each step to the board UI.
- Configurable tick speed, auto-reset on game end, deterministic toggle.
- Uses the loaded model (or random legal if no model loaded).

### JSONL watcher (training metrics)
- The backend can tail a JSONL file and broadcast the latest entry over WS.
- Use `POST /training/watch` to start watching a path; the UI shows the latest object.
- Example JSONL line:
  - `{ "timesteps": 12000, "reward": 0.42, "eval_score": 0.35 }`

## 5) SB3 Migration

The SIMPLE framework has been ported from `stable_baselines` (v2, PPO1 + mpi4py) to `stable_baselines3` (PPO + PyTorch).

Ported files:
- `app/utils/agents.py` — SB3 `get_distribution()` for action probs
- `app/utils/files.py` — SB3 `PPO.load()`, no mpi4py
- `app/utils/selfplay.py` — gymnasium 5-tuple step
- `app/utils/callbacks.py` — SB3 `EvalCallback`, no MPI
- `app/train.py` — SB3 PPO with selfplay
- `app/test.py` — SB3 imports, gymnasium step

Training:
- `docker compose exec app python3 train.py -r -e cubalibre`
- Models saved to `zoo/cubalibre/`

## 6) Notes / constraints
- Run the backend from the repo root so Python can resolve the `app` package.
- The UI assumes 13 spaces (matches current env model).
- Pretrained models for other games (tictactoe, connect4, etc.) are SB2 format and won't load with SB3.
