from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

import asyncio
import json
from pathlib import Path
from datetime import datetime
import os
import uuid
import time
import numpy as np

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .env_instance import env_instance
from .serialization import serialize_env
from .model_manager import ModelManager


app = FastAPI(title="SIMPLE WebUI Backend", version="0.1.0")

_WEBUI_DIR = Path(__file__).resolve().parents[2]
_IMAGES_DIR = _WEBUI_DIR / "images"
app.mount("/assets", StaticFiles(directory=str(_IMAGES_DIR)), name="assets")
_LOG_DIR = _WEBUI_DIR.parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Auto-initialize environment on startup to prevent 500s on frontend load
    print("Auto-initializing environment...")
    try:
        env_instance.reset()
        print("Environment initialized.")
    except Exception as e:
        print(f"Failed to auto-initialize environment: {e}")

# ---------------------------------------------------------------------------
# Pydantic request / response models
# ---------------------------------------------------------------------------


class StepRequest(BaseModel):
    action: int = Field(..., ge=0)


class StepResponse(BaseModel):
    reward: Any
    terminated: bool
    truncated: bool
    state: Dict[str, Any]


class ModelLoadRequest(BaseModel):
    path: str
    device: Optional[str] = None
    algo: str = "PPO"


class ResetRequest(BaseModel):
    faction_roles: Optional[Dict[str, str]] = None  # {"0":"human","1":"ai",...}
    scenario: Optional[str] = "standard"


class FactionRolesRequest(BaseModel):
    faction_roles: Dict[str, str]  # {"0":"human","1":"ai","2":"ai","3":"human"}


class SpectatorStartRequest(BaseModel):
    tick_ms: int = Field(500, ge=50, le=10000)
    deterministic: bool = False
    auto_reset: bool = True


class TrainingWatchRequest(BaseModel):
    path: Optional[str] = None
    poll_seconds: float = Field(1.0, ge=0.2, le=30.0)


# ---------------------------------------------------------------------------
# Server-side game session state
# ---------------------------------------------------------------------------

# Faction roles: maps faction index (0-3) -> "human" | "ai"
# Default: faction 0 (GOVT) is human, rest are AI
_faction_roles: Dict[int, str] = {0: "human", 1: "ai", 2: "ai", 3: "ai"}

_ws_clients: Set[WebSocket] = set()
_ws_lock = asyncio.Lock()
model_manager = ModelManager()

_last_action: Optional[int] = None
_last_actor: Optional[int] = None
_game_id: str = str(uuid.uuid4())
_game_step_count: int = 0

# Spectator (AI-vs-AI demo) state
_spectator_task: Optional[asyncio.Task] = None
_spectator_running = False
_spectator_tick_ms: int = 500
_spectator_deterministic: bool = False
_spectator_auto_reset: bool = True

# Training JSONL watcher state
_training_status: Dict[str, Any] = {
    "path": None,
    "data": None,
    "error": None,
    "updated_at": None,
}
_training_watch: Dict[str, Any] = {"path": None, "poll": 1.0}
_training_watch_task: Optional[asyncio.Task] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _log_game_step(
    actor: int, action: int, reward: Any, done: bool, info: Any, type: str = "unknown"
) -> None:
    global _game_step_count
    _game_step_count += 1
    
    entry = {
        "timestamp": time.time(),
        "game_id": _game_id,
        "step": _game_step_count,
        "actor": actor,
        "action": int(action),
        "reward": reward,
        "done": done,
        "type": type,
        # We could add state summary here if needed
    }
    try:
        with open(_LOG_DIR / "game_history.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        print(f"Failed to log game step: {e}")


def _set_faction_roles(roles: Optional[Dict[str, str]]) -> None:
    global _faction_roles
    if roles is None:
        return
    for k, v in roles.items():
        idx = int(k)
        if idx < 0 or idx > 3:
            continue
        _faction_roles[idx] = "human" if v.lower().startswith("h") else "ai"


def _is_human_turn() -> bool:
    try:
        env = env_instance.get()
    except RuntimeError:
        return True
    return _faction_roles.get(env.current_player_num, "ai") == "human"


def _set_last_action(action: Optional[int], actor: Optional[int]) -> None:
    global _last_action, _last_actor
    _last_action = int(action) if action is not None else None
    _last_actor = int(actor) if actor is not None else None


def _state_metadata(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    meta = {
        "last_action": _last_action,
        "last_actor": _last_actor,
        "model": model_manager.info(),
        "faction_roles": {str(k): v for k, v in _faction_roles.items()},
        "spectator": {"running": _spectator_running, "tick_ms": _spectator_tick_ms},
        "training": _training_status.get("data"),
        "training_error": _training_status.get("error"),
        "training_updated_at": _training_status.get("updated_at"),
    }
    if extra:
        meta.update(extra)
    return meta


def _pick_random_legal(env) -> Optional[int]:
    mask = np.asarray(env.legal_actions, dtype=np.int64)
    indices = np.nonzero(mask)[0]
    if len(indices) == 0:
        return None
    return int(np.random.choice(indices))


async def _ai_step(env, deterministic: bool = False) -> tuple:
    """Execute one AI step. Uses model if loaded, else random legal."""
    actor = env.current_player_num
    if model_manager.info().get("loaded"):
        action, info = model_manager.pick_action(
            env,
            deterministic=deterministic,
            mask_invalid=True,
        )
    else:
        action = _pick_random_legal(env)
        if action is None:
            raise RuntimeError("No legal actions available for AI step.")
        info = {"random": True}
    
    obs, reward, terminated, truncated, _info = env.step(int(action))
    _set_last_action(int(action), actor)
    
    # Log AI step
    _log_game_step(
        actor=actor,
        action=int(action),
        reward=reward,
        done=terminated or truncated,
        info=info,
        type="ai"
    )

    return action, actor, info, reward, terminated, truncated


async def _advance_ai_turns(
    env,
    *,
    deterministic: bool = False,
    broadcast: bool = True,
    max_steps: int = 500,
) -> Dict[str, Any]:
    """Advance all consecutive AI turns. Stop at human turn or game end."""
    steps = 0
    terminated = False
    truncated = False
    while steps < max_steps and not (terminated or truncated):
        if _faction_roles.get(env.current_player_num, "ai") == "human":
            break
        # Safety: if no legal actions exist, stop (game may have ended)
        mask = np.asarray(env.legal_actions, dtype=np.int64)
        if not np.any(mask):
            break
        _action, _actor, _info, _reward, terminated, truncated = await _ai_step(
            env, deterministic=deterministic
        )
        steps += 1

    state = serialize_env(env, metadata=_state_metadata({"ai_steps": steps}))
    if broadcast:
        await _broadcast_state(state)
    return state


# ---------------------------------------------------------------------------
# Training JSONL watcher
# ---------------------------------------------------------------------------


def _update_training_status(data: Optional[Dict[str, Any]], error: Optional[str] = None) -> None:
    _training_status["data"] = data
    _training_status["error"] = error
    _training_status["updated_at"] = datetime.utcnow().isoformat() + "Z"


def _read_last_json_line(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return None
    size = path.stat().st_size
    if size == 0:
        return None
    block_size = min(65536, size)
    with path.open("rb") as handle:
        handle.seek(-block_size, os.SEEK_END)
        chunk = handle.read(block_size).decode("utf-8", errors="ignore")
    lines = [line.strip() for line in chunk.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return None


# ---------------------------------------------------------------------------
# WebSocket broadcasting
# ---------------------------------------------------------------------------


async def _broadcast_state(state: Dict[str, Any]) -> None:
    async with _ws_lock:
        clients = list(_ws_clients)
    if not clients:
        return
    dead: List[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_json({"type": "state", "payload": state})
        except Exception:
            dead.append(ws)
    if dead:
        async with _ws_lock:
            for ws in dead:
                _ws_clients.discard(ws)


async def _broadcast_training(status: Dict[str, Any]) -> None:
    async with _ws_lock:
        clients = list(_ws_clients)
    if not clients:
        return
    dead: List[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_json({"type": "training", "payload": status})
        except Exception:
            dead.append(ws)
    if dead:
        async with _ws_lock:
            for ws in dead:
                _ws_clients.discard(ws)


# ---------------------------------------------------------------------------
# Spectator loop (AI-vs-AI with per-step broadcast)
# ---------------------------------------------------------------------------


async def _spectator_loop() -> None:
    global _spectator_running
    _spectator_running = True
    try:
        while _spectator_running:
            try:
                env = env_instance.get()
            except RuntimeError:
                env = env_instance.reset()

            done = getattr(env, "done", False)
            if done:
                if _spectator_auto_reset:
                    env = env_instance.reset()
                    # Assign new game ID for spectator reset
                    global _game_id, _game_step_count
                    _game_id = str(uuid.uuid4())
                    _game_step_count = 0
                    
                    state = serialize_env(env, metadata=_state_metadata({"spectator_event": "reset"}))
                    await _broadcast_state(state)
                    await asyncio.sleep(_spectator_tick_ms / 1000.0)
                    continue
                else:
                    _spectator_running = False
                    break

            _action, _actor, _info, _reward, terminated, truncated = await _ai_step(
                env, deterministic=_spectator_deterministic
            )
            state = serialize_env(
                env,
                metadata=_state_metadata(
                    {
                        "spectator_event": "step",
                        "spectator_action": _action,
                        "spectator_actor": _actor,
                    }
                ),
            )
            await _broadcast_state(state)

            if terminated or truncated:
                if _spectator_auto_reset:
                    await asyncio.sleep(_spectator_tick_ms / 1000.0)
                    continue
                else:
                    _spectator_running = False
                    break

            await asyncio.sleep(_spectator_tick_ms / 1000.0)
    except asyncio.CancelledError:
        pass
    finally:
        _spectator_running = False


async def _training_watch_loop() -> None:
    last_payload: Optional[Dict[str, Any]] = None
    while True:
        path = _training_watch.get("path")
        poll = float(_training_watch.get("poll", 1.0))
        if not path:
            await asyncio.sleep(1.0)
            continue
        try:
            payload = _read_last_json_line(Path(path))
            if payload is not None and payload != last_payload:
                _update_training_status(payload)
                await _broadcast_training(_training_status)
                last_payload = payload
        except Exception as exc:
            _update_training_status(None, error=str(exc))
            await _broadcast_training(_training_status)
        await asyncio.sleep(poll)


@app.on_event("startup")
async def _startup() -> None:
    global _training_watch_task
    if _training_watch_task is None:
        _training_watch_task = asyncio.create_task(_training_watch_loop())


@app.on_event("shutdown")
async def _shutdown() -> None:
    global _training_watch_task, _spectator_task
    if _training_watch_task is not None:
        _training_watch_task.cancel()
        _training_watch_task = None
    if _spectator_task is not None:
        _spectator_task.cancel()
        _spectator_task = None


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/reset")
async def reset_env(req: Optional[ResetRequest] = None) -> Dict[str, Any]:
    # Stop spectator if running
    global _spectator_task, _spectator_running
    if _spectator_task is not None:
        _spectator_running = False
        _spectator_task.cancel()
        _spectator_task = None

    if req and req.faction_roles:
        _set_faction_roles(req.faction_roles)

    # Initialize new game ID
    global _game_id, _game_step_count
    _game_id = str(uuid.uuid4())
    _game_step_count = 0

    env = env_instance.reset(options={"scenario": req.scenario} if req and req.scenario else None)
    _set_last_action(None, None)
    state = serialize_env(env, metadata=_state_metadata())
    await _broadcast_state(state)


    # If the first turn is AI, auto-advance
    if not _is_human_turn():
        state = await _advance_ai_turns(env)

    return state


@app.get("/state")
def get_state() -> Dict[str, Any]:
    env = env_instance.get()
    return serialize_env(env, metadata=_state_metadata())


@app.get("/legal_actions")
def get_legal_actions() -> Dict[str, Any]:
    env = env_instance.get()
    return serialize_env(env)["legal_actions"]


@app.post("/faction_roles")
async def set_faction_roles(req: FactionRolesRequest) -> Dict[str, Any]:
    _set_faction_roles(req.faction_roles)
    try:
        env = env_instance.get()
        # If current turn became AI, auto-advance
        if not _is_human_turn() and not getattr(env, "done", False):
            state = await _advance_ai_turns(env)
        else:
            state = serialize_env(env, metadata=_state_metadata())
            await _broadcast_state(state)
    except RuntimeError:
        state = {"faction_roles": {str(k): v for k, v in _faction_roles.items()}}
    return state


@app.get("/faction_roles")
def get_faction_roles() -> Dict[str, Any]:
    return {"faction_roles": {str(k): v for k, v in _faction_roles.items()}}


@app.post("/step", response_model=StepResponse)
async def step(req: StepRequest) -> StepResponse:
    env = env_instance.get()
    actor = env.current_player_num
    obs, reward, terminated, truncated, _info = env.step(int(req.action))
    _set_last_action(int(req.action), actor)

    # Log Human step
    _log_game_step(
        actor=actor,
        action=int(req.action),
        reward=reward,
        done=terminated or getattr(env, "done", False),
        info=_info,
        type="human"
    )

    state = serialize_env(env, metadata=_state_metadata())
    await _broadcast_state(state)

    # Auto-advance AI turns after human step
    if not (terminated or truncated) and not _is_human_turn():
        state = await _advance_ai_turns(env)

    return StepResponse(
        reward=reward,
        terminated=bool(terminated or getattr(env, "done", False)),
        truncated=bool(truncated),
        state=state,
    )


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------

@app.get("/models")
@app.get("/models/")
def list_models() -> List[Dict[str, str]]:
    """List available models in zoo and logs."""
    models = []
    
    # 1. Zoo
    zoo_dir = _WEBUI_DIR.parent / "zoo" / "cubalibre"
    if zoo_dir.exists():
        for f in zoo_dir.glob("*.zip"):
            models.append({
                "name": f.name,
                "path": str(f.absolute()),
                "source": "zoo"
            })

    # 2. Checkpoints
    logs_dir = _WEBUI_DIR.parent / "logs" / "checkpoints"
    if logs_dir.exists():
        for f in logs_dir.glob("*.zip"):
            models.append({
                "name": f.name,
                "path": str(f.absolute()),
                "source": "checkpoint"
            })
            
    # Sort by name
    models.sort(key=lambda x: x["name"])
    return models


@app.post("/model/load")
async def model_load(req: ModelLoadRequest) -> Dict[str, Any]:
    try:
        env = env_instance.get()
    except RuntimeError:
        env = None
    model_manager.load(req.path, env=env, device=req.device, algo=req.algo)
    if env is not None:
        state = serialize_env(env, metadata=_state_metadata())
        await _broadcast_state(state)
    return model_manager.info()


@app.post("/model/unload")
async def model_unload() -> Dict[str, Any]:
    model_manager.unload()
    try:
        env = env_instance.get()
        state = serialize_env(env, metadata=_state_metadata())
        await _broadcast_state(state)
    except RuntimeError:
        pass
    return model_manager.info()


@app.get("/model/info")
def model_info() -> Dict[str, Any]:
    return model_manager.info()


# ---------------------------------------------------------------------------
# Spectator mode (AI-vs-AI on the board)
# ---------------------------------------------------------------------------


@app.post("/spectator/start")
async def spectator_start(req: Optional[SpectatorStartRequest] = None) -> Dict[str, Any]:
    global _spectator_task, _spectator_running, _spectator_tick_ms, _spectator_deterministic, _spectator_auto_reset

    # Stop existing
    if _spectator_task is not None:
        _spectator_running = False
        _spectator_task.cancel()
        _spectator_task = None

    if req:
        _spectator_tick_ms = req.tick_ms
        _spectator_deterministic = req.deterministic
        _spectator_auto_reset = req.auto_reset

    # Set all factions to AI for spectator
    for i in range(4):
        _faction_roles[i] = "ai"

    # Reset env
    env = env_instance.reset()
    _set_last_action(None, None)
    state = serialize_env(env, metadata=_state_metadata({"spectator_event": "start"}))
    await _broadcast_state(state)

    _spectator_task = asyncio.create_task(_spectator_loop())
    return {"status": "started", "tick_ms": _spectator_tick_ms}


@app.post("/spectator/stop")
async def spectator_stop() -> Dict[str, Any]:
    global _spectator_task, _spectator_running
    if _spectator_task is not None:
        _spectator_running = False
        _spectator_task.cancel()
        _spectator_task = None
    try:
        env = env_instance.get()
        state = serialize_env(env, metadata=_state_metadata({"spectator_event": "stopped"}))
        await _broadcast_state(state)
    except RuntimeError:
        pass
    return {"status": "stopped"}


@app.post("/spectator/speed")
async def spectator_speed(tick_ms: int = 500) -> Dict[str, Any]:
    global _spectator_tick_ms
    _spectator_tick_ms = max(50, min(10000, tick_ms))
    return {"tick_ms": _spectator_tick_ms}


@app.get("/spectator/status")
def spectator_status() -> Dict[str, Any]:
    return {
        "running": _spectator_running,
        "tick_ms": _spectator_tick_ms,
        "deterministic": _spectator_deterministic,
        "auto_reset": _spectator_auto_reset,
    }


# ---------------------------------------------------------------------------
# Training JSONL watcher
# ---------------------------------------------------------------------------


@app.post("/training/watch")
async def watch_training(req: TrainingWatchRequest) -> Dict[str, Any]:
    _training_watch["path"] = req.path
    _training_watch["poll"] = float(req.poll_seconds)
    _training_status["path"] = req.path
    if not req.path:
        _update_training_status(None, error=None)
    return {"watch": dict(_training_watch), "status": dict(_training_status)}


@app.get("/training/status")
def training_status() -> Dict[str, Any]:
    return dict(_training_status)


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    async with _ws_lock:
        _ws_clients.add(ws)

    try:
        env = env_instance.get()
        await ws.send_json({"type": "state", "payload": serialize_env(env, metadata=_state_metadata())})
    except Exception:
        await ws.send_json({"type": "info", "payload": {"message": "Env not initialized. Call /reset."}})

    if _training_status.get("data") or _training_status.get("error"):
        await ws.send_json({"type": "training", "payload": dict(_training_status)})

    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with _ws_lock:
            _ws_clients.discard(ws)
