# Repository Guidelines

## Project Overview

Cuba Libre 2018 rules engine for RL training via the SIMPLE framework. Single policy acts as any faction. Full campaign, no COIN bots. Authoritative spec: `RULES_SPEC.md`. Task tracking: `TASKS.md`.

## File Map

```
app/
  train.py                          # SB3 PPO training with selfplay
  test.py                           # SB3 evaluation runner
  config.py                         # MODELDIR="zoo", LOGDIR="logs"
  utils/
    agents.py                       # Agent class, action prob utilities (SB3)
    files.py                        # Model load/save utilities (SB3)
    selfplay.py                     # SelfPlayEnv wrapper (gymnasium 5-tuple)
    callbacks.py                    # SelfPlayCallback (SB3 EvalCallback)
    register.py                     # Env + policy registration
  models/cubalibre/models.py        # CubaLibreExtractor + CustomPolicy (SB3)
  environments/cubalibre/envs/
    env.py                          # CubaLibreEnv (gymnasium, ~6500 lines)
    events.py                       # All 48 event card implementations
    data.py                         # Card text data (cards 1–48)
    classes.py                      # Space, Player, Card classes
    constants.py                    # Shared constants
    action_calc.py                  # Action space utilities

webui/
  backend/app/
    main.py                         # FastAPI + WebSocket server
    model_manager.py                # SIMPLE Agent wrapper for WebUI
    env_instance.py                 # Env singleton
    serialization.py                # State → JSON serializer
  frontend/src/
    App.jsx                         # React UI
    api.js                          # REST/WS client
    mapLayout.js                    # Space hitbox coordinates
    styles.css                      # Layout styles
  docs/
    RUN_AND_INTEGRATION.md          # Backend/frontend startup, endpoint list
    ARCHITECTURE.md                 # Design notes
    STATE_SCHEMA.md                 # JSON state format

tests/cubalibre/                    # 130 files, 304 test methods
zoo/cubalibre/                      # best_model.zip, final_model.zip
logs/                               # Training run logs (cubalibre_ppo_1..5)
scripts/
  test_webui.fish                   # End-to-end smoke test (nix develop)
  train_cubalibre_long.fish         # Long training run
```

## Architecture

- **Env**: `CubaLibreEnv` is a gymnasium env with 10 decision phases and `Discrete(699)` action space with phase-dependent masking.
- **Training**: SB3 PPO with selfplay wrapper. Models saved to `zoo/cubalibre/`.
- **WebUI backend**: FastAPI serving env state over REST + WebSocket. Faction roles (human/AI per faction), spectator mode, auto-advance AI turns.
- **WebUI frontend**: React + Vite. Phase-aware controls, map hitboxes, spectator controls.
- **SB3 migration**: All SIMPLE utils ported from stable_baselines v2 (PPO1 + mpi4py + TF) to stable_baselines3 (PPO + PyTorch). Pretrained models for other games (tictactoe, connect4, etc.) in `app/zoo/pretrained/` are SB2 format and won't load.

## Build, Test, and Development Commands

### Docker (training + tests)
- `docker compose up -d app` — start container
- `docker compose exec app python -m unittest discover -s tests -p "test_*.py" -b` — full test suite
- `docker compose exec app python -m unittest -q tests.cubalibre.test_propaganda_victory_checks` — single module
- `docker compose exec app python3 train.py -r -e cubalibre` — SB3 training
- `docker compose exec app python3 test.py -g 100 -a best_model base base -e cubalibre` — evaluation

### Nix + venv (local dev)
- `nix develop` or scripts use `#!/usr/bin/env nix` shebang
- Venv at `.venv/bin/activate.fish`
- `PYTHONPATH` needs `app:app/environments` for imports outside Docker

### WebUI
- Backend: `python -m uvicorn webui.backend.app.main:app --reload --port 8000` (from repo root)
- Frontend: `cd webui/frontend && npm install && npm run dev` (serves on :5173)
- Smoke test: `./scripts/test_webui.fish`

### Troubleshooting
- `service "app" is not running` → `docker compose up -d app`
- `No module named 'tests'` or `No module named 'app'` → run from repo root, check Docker mounts `/workspace`

## Coding Style & Naming Conventions
- Python: 4-space indent, PEP 8, no formatter configured. Match surrounding files.
- `snake_case` for functions/variables, `PascalCase` for classes, lowercase module names.

## Testing Guidelines
- Standard library `unittest`. Pattern: `tests/**/test_*.py` with `Test*` classes and `test_*` methods.
- Prefer Docker for tests to avoid nix store growth.
- Proceed with running verification/test commands without asking in chat; rely on the IDE prompt for actual command approval.

## Commit & Pull Request Guidelines
- Short imperative summaries: `fix: limit gym version`, `add: cubalibre events`.
- Include test commands run. Add screenshots/logs for visual or training changes.

## Security & Configuration Tips
- Prefer `docker compose exec app` for training/evaluation.
- Don't overwrite pretrained models without noting the change.
- Cuba Libre models live at `zoo/cubalibre/` (repo root), not `app/zoo/pretrained/`.
