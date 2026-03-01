from __future__ import annotations

import sys
import os
from typing import Any, Dict, Optional, Tuple

import numpy as np

# Add the SIMPLE app directory to sys.path so we can import its utilities.
_APP_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "app")
if os.path.isdir(_APP_DIR) and _APP_DIR not in sys.path:
    sys.path.insert(0, os.path.abspath(_APP_DIR))


class ModelManager:
    """Wraps a SIMPLE Agent backed by an SB3 PPO model for the WebUI."""

    def __init__(self) -> None:
        self._model = None
        self._agent = None  # utils.agents.Agent instance
        self._path: Optional[str] = None
        self._device: Optional[str] = None
        self._algo: Optional[str] = None
        self._last_error: Optional[str] = None

    def unload(self) -> None:
        self._model = None
        self._agent = None
        self._path = None
        self._device = None
        self._algo = None
        self._last_error = None

    def info(self) -> Dict[str, Any]:
        return {
            "loaded": self._model is not None,
            "path": self._path,
            "device": self._device,
            "algo": self._algo,
            "error": self._last_error,
        }

    def load(self, path: str, env=None, device: Optional[str] = None, algo: str = "PPO") -> None:
        self._last_error = None
        algo = algo.upper()
        try:
            from sb3_contrib import MaskablePPO
            from stable_baselines3 import PPO
        except ImportError as exc:
            self._last_error = "stable-baselines3 / sb3-contrib not installed"
            raise RuntimeError(
                "stable-baselines3 and sb3-contrib are required for model loading. Install app/requirements.txt."
            ) from exc

        if algo not in ("PPO", "MASKABLEPPO"):
            self._last_error = f"Unsupported algo: {algo}"
            raise RuntimeError(f"Unsupported algo: {algo}")

        self._device = device or "auto"

        try:
            self._model = MaskablePPO.load(path, env=env, device=self._device)
            self._algo = "MaskablePPO"
        except Exception:
            self._model = PPO.load(path, env=env, device=self._device)
            self._algo = "PPO"
        
        self._path = path

        # Wrap in a SIMPLE Agent so the WebUI uses the same logic as training/test
        from utils.agents import Agent
        self._agent = Agent("webui_model", self._model)

    def pick_action(
        self,
        env,
        deterministic: bool = False,
        mask_invalid: bool = True,
    ) -> Tuple[int, Dict[str, Any]]:
        """Pick an action using the SIMPLE Agent interface."""
        if self._agent is None or self._model is None:
            raise RuntimeError("Model not loaded.")

        info: Dict[str, Any] = {"masked": mask_invalid}
        action = self._agent.choose_action(
            env,
            choose_best_action=deterministic,
            mask_invalid_actions=mask_invalid,
        )
        return int(action), info

    def pick_action_raw(
        self,
        observation: np.ndarray,
        legal_actions: Optional[np.ndarray] = None,
        deterministic: bool = False,
        mask_invalid: bool = True,
    ) -> Tuple[int, Dict[str, Any]]:
        """Pick action from raw arrays (no env required). Fallback path."""
        if self._model is None:
            raise RuntimeError("Model not loaded.")

        info: Dict[str, Any] = {"masked": False, "fallback": False}

        # Check if we can use MaskablePPO predict directly
        # SB3 MaskablePPO.predict supports action_masks arg
        try:
            masks = legal_actions if mask_invalid and legal_actions is not None else None
            action, _state = self._model.predict(
                observation,
                deterministic=deterministic,
                action_masks=masks
            )
            if isinstance(action, np.ndarray):
                action = action.item()
            
            if masks is not None:
                info["masked"] = True
            
            return int(action), info

        except TypeError:
            # Fallback for standard PPO (does not support action_masks)
            from utils.agents import get_action_probs_sb3, mask_actions, sample_action

            action_probs = get_action_probs_sb3(self._model, observation)

            if mask_invalid and legal_actions is not None:
                action_probs = mask_actions(legal_actions, action_probs)
                info["masked"] = True

            if deterministic:
                action = int(np.argmax(action_probs))
            else:
                action = int(sample_action(action_probs))

            # Verify legality, fallback if needed
            if legal_actions is not None and int(legal_actions[action]) == 0:
                legal = np.nonzero(np.asarray(legal_actions, dtype=np.int64))[0]
                if len(legal) == 0:
                    raise RuntimeError("No legal actions available.")
                action = int(np.random.choice(legal))
                info["fallback"] = True

            return int(action), info
