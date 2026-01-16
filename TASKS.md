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

---

## What's Actually Left

### High Priority — Verification

These have not been run against the ported SB3 code yet.

1. **End-to-end smoke test** — Run `scripts/test_webui.fish` to verify backend starts, endpoints respond, model loads from `zoo/cubalibre/best_model.zip`, and frontend serves.

2. **Unit tests against SB3 code** — The 304 tests exercise the env (which is unchanged), but the SB3-ported `agents.py`/`selfplay.py`/`callbacks.py`/`train.py` haven't been integration-tested yet.
   - `docker compose exec app python -m unittest discover -s tests -p "test_*.py" -b`

3. **Training smoke test** — Verify SB3 training actually runs and produces a model:
   - `docker compose exec app python3 train.py -r -e cubalibre`
   - Or: `./scripts/train_cubalibre_long.fish reset`

### Medium Priority — Functional Gaps

4. **Frontend Ops/LimOps phase controls** — Phases 2, 3, 4 (op selection, limited ops, special activity) currently fall back to raw action ID input. These need proper button-based controls that decode op types and space targets into readable choices.

5. **Game-over display** — Frontend doesn't visually indicate when the game ends or who won. The backend returns `done` state but the UI doesn't react to it.

6. **Training metrics hook** — The training watch panel exists but there's no JSONL emitter in the SB3 training loop. Add a callback that writes `{"timesteps": N, "reward": R, ...}` to a JSONL file so the UI can display live training progress.

### Low Priority — Polish & Future

7. **Agent piece selection within spaces** — When multiple pieces of the same faction exist in one space, selection is deterministic ("first available"). Could add a `PHASE_CHOOSE_TARGET_PIECE` flow for these edge cases. Impact is minimal — current behavior follows rulebook where specified.

8. **Scenario support** — Currently hardcoded to full campaign setup. Future: add setup modules for shorter scenarios (no changes needed to the core rules engine).

9. **Maskable PPO** — SB3 standard PPO doesn't support action masks natively. The current approach (mask + renormalize probabilities in `agents.py`) works but is a workaround. Consider switching to `sb3-contrib` `MaskablePPO` for cleaner integration.

10. **Other game environments** — Pretrained models for tictactoe, connect4, sushigo, etc. in `app/zoo/pretrained/` are SB2 format and won't load with SB3. These would need their own model policies ported if anyone wants to use them again.

