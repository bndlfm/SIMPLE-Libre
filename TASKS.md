# SIMPLE-Libre Task Tracker

See `AGENTS.md` for project overview, file map, build commands, and architecture.

---

## What's Done

### Rules Engine (complete)

The Cuba Libre environment is a fully phase-based gymnasium environment with all core mechanics implemented.

**Core files:**
- `app/environments/cubalibre/envs/env.py` — 6473-line `CubaLibreEnv` (gymnasium)
- `app/environments/cubalibre/envs/events.py` — 752 lines, all 48 event cards
- `app/environments/cubalibre/envs/data.py` — card text for cards 1–48
- `app/environments/cubalibre/envs/classes.py` — game objects (Space, Player, Card)
- `app/environments/cubalibre/envs/constants.py` — shared constants
- `app/environments/cubalibre/envs/action_calc.py` — action space utilities

**Phase-based state machine** (10 phases):
- `PHASE_CHOOSE_MAIN` (Pass / Event / Ops)
- `PHASE_CHOOSE_EVENT_SIDE` (Unshaded / Shaded)
- `PHASE_CHOOSE_OP_ACTION` (full ops with SA)
- `PHASE_CHOOSE_LIMITED_OP_ACTION` (limited ops, no SA)
- `PHASE_CHOOSE_SPECIAL_ACTIVITY`
- `PHASE_CHOOSE_TARGET_SPACE`
- `PHASE_CHOOSE_TARGET_FACTION`
- `PHASE_CHOOSE_EVENT_OPTION`
- `PHASE_CHOOSE_TARGET_PIECE`
- `PHASE_PROPAGANDA_REDEPLOY_MENU`

**Action space**: `Discrete(699)` with phase-dependent masking:
- 0–2: main choice
- 3–4: event side
- 5–342: full ops (op × space)
- 343: enter limited ops
- 344–681: limited ops (op × space)
- 682–694: target space selection
- 695–698: target faction selection

**COIN turn structure**: Fully implemented per 2018 rules:
- Card-driven eligibility order, 2-action-per-card enforcement
- 1st/2nd actor constraints (Event→LimOps only, Ops→Event or LimOps, Pass→Event or full Ops)
- Cross-card eligibility (`ineligible_next_card`, `ineligible_through_next_card`)
- Event-driven "stay eligible" support
- Launder mechanic (2.3.6)

**2018 campaign tracks**:
- Aid (0–49), US Alliance (Firm/Reluctant/Embargoed)
- Derived victory markers: Total Support, Opposition+Bases, DR Pop+Bases, Open Casinos
- All included in observation

**Propaganda round** (full 2018 procedure):
- 6.1 Victory Phase with threshold checks
- 6.2.1 Govt Earnings (econ + Aid, sabotage exclusion)
- 6.2.2 Insurgent Earnings (M26/DR/Syndicate)
- 6.2.3 The Skim (with Trafficante_Shaded blocking)
- 6.2.4 Cash Deposits
- 6.3.1 US Alliance/Aid degradation
- 6.4 Redeploy (police relocation, mandatory troops, agent-driven optional troops)
- 6.5 Reset (eligibility, terror/sabotage clear, guerrillas underground, capability expiry)
- Final-round exceptions (Support Phase only, no Redeploy/Reset per 6.3.5)
- Victory margin ties per 7.1/7.3

**All 48 event cards**: Implemented with agent-driven target selection. Each card has dedicated test coverage. Cards 11/13/18 blank-side masking handled.

**Cash system**: Per-piece cash holders, faction-owned transfers, removal-triggered transfer choices, casino stacking rules (1.4.2).

### Tests (complete)

- **130 test files**, **304 test methods** under `tests/cubalibre/`
- All 48 event cards have test coverage
- Propaganda, victory, eligibility, tracks, cash, casinos, capabilities all tested
- Run: `docker compose exec app python -m unittest discover -s tests -p "test_*.py" -b`

### SB3 Migration (complete)

Ported the SIMPLE framework from `stable_baselines` (v2, PPO1 + mpi4py + TensorFlow) to `stable_baselines3` (PPO + PyTorch + gymnasium).

**Ported files:**
- `app/utils/agents.py` — SB3 `get_distribution()` for action probs, `predict_values()`
- `app/utils/files.py` — SB3 `PPO.load()`, removed mpi4py
- `app/utils/selfplay.py` — gymnasium 5-tuple step returns
- `app/utils/callbacks.py` — SB3 `EvalCallback`, removed MPI
- `app/train.py` — SB3 PPO with selfplay wrapper
- `app/test.py` — SB3 imports, gymnasium step

**Model policy**: `app/models/cubalibre/models.py` — `CubaLibreExtractor` + `CustomPolicy` (already SB3-native).

**Trained models**: `zoo/cubalibre/best_model.zip`, `zoo/cubalibre/final_model.zip`

**Training logs**: `logs/cubalibre_ppo_1/` through `logs/cubalibre_ppo_5/`

### Web UI (complete)

**Backend** (`webui/backend/app/`):
- FastAPI server with WebSocket state broadcasting
- `model_manager.py` — wraps SIMPLE `Agent` class for SB3 model loading and action selection
- Faction roles (any combo of human/AI for 4 factions)
- Auto-advance AI turns after human step
- Spectator mode (AI-vs-AI with configurable tick speed)
- Training JSONL watcher

**Frontend** (`webui/frontend/`):
- React + Vite
- Faction role picker (toggle each faction human/AI)
- Phase-aware controls (CHOOSE_MAIN, EVENT_SIDE, TARGET_SPACE, TARGET_FACTION, EVENT_OPTION)
- SVG map with clickable space hitboxes
- Spectator start/stop/speed controls
- Card display, tracks, player info, legal actions

**Docs**: `webui/docs/RUN_AND_INTEGRATION.md`, `webui/docs/ARCHITECTURE.md`, `webui/docs/STATE_SCHEMA.md`

### Piece Selection Logic (complete)

**Piece Selection**:
- **Assault (Govt)**: Implemented target faction selection (when multiple eligible) and corrected removal priority (Active G -> Base -> Underground G).
- **Attack (Insurgents)**: Implemented piece type selection (Troops vs Police vs Base) when multiple types are eligible.
- **Paused Flow**: Implemented `PHASE_CHOOSE_EVENT_OPTION` / `PHASE_CHOOSE_TARGET_FACTION` loops for multi-step removal operations.

### Model Integration (complete)

**Web UI AI**:
- Refactored `ModelManager` to use `MaskablePPO` natively.
- Added Backend `GET /models` and Frontend `ModelSelector.jsx`.
- Validated model loading and device handling.

### Scenario Support (complete)

**Scenario Selection**:
- **Short Game**: Implemented deck modification logic (remove 8 random events) in `Deck.py`.
- **Backend**: Updated `reset()` and API to accept `scenario` parameter.
- **Frontend**: Added Scenario dropdown to New Game UI.


---

## What's Actually Left

### High Priority — Verification
 
1. **End-to-end smoke test** (Complete) — Verifying user confirmation that E2E tests are passing.
 
2. **Unit tests against SB3 code** (Complete) — 304 unit tests passing.
 
3. **Training smoke test** (Complete) — Training loop verified with new logging hooks.

4. **Fix Sweep Fizzle Bug**
   - [x] Diagnose `SWEEP_SRC` no valid target error (Hypothesis: Stale `_pending_event_target` shadows Op logic).
   - [x] Verify hypothesis with reproduction script.
   - [x] Fix: Ensure `step()` clears event state when starting Ops.

### Medium Priority — Functional Gaps
 
4. **Frontend Ops/LimOps phase controls** (Complete) — Implemented `OpsPanel` in `App.jsx`, verified backend `action_ranges`.
 
5. **Game-over display** (Complete) — Implemented Backend `points` serialization and Frontend `GameOverModal` in `App.jsx`.
 
6. **Training metrics hook** (Complete) — Added `SelfPlayCallback` JSONL logging to `logs/training.jsonl`.
 
7. **Game History Logging** (Complete) — Implemented `GameLogger` in `main.py` to write `logs/game_history.jsonl`.
 
### Low Priority — Polish & Future
 
 9. **Scene support** (Complete) — Implemented "Short Game" scenario (remove 8 random cards). "Variable Deployment" remains out of scope as it requires complex interactive setup.

 
 
 11. **Other game environments** (Deleted) — Removed legacy SB2 environments/models (TicTacToe, Connect4, etc.) to keep the codebase clean.

## Frontend UI Rendering Completed
- Implemented mapping logic of piece tokens from backend game state to render visually on map
- Fixed _clear_pending state sync issues and Mosquera / SIM rule calculation bugs in backend
