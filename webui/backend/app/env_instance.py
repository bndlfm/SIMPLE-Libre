from __future__ import annotations

from typing import Optional


class EnvInstance:
    """Holds the current env instance.

    The UI backend owns the env and exposes it over HTTP/WS.
    """

    def __init__(self) -> None:
        self._env = None

    def get(self):
        if self._env is None:
            raise RuntimeError("Environment not initialized. Call /reset first.")
        return self._env

    def reset(self):
        # Import lazily so backend can start even if some heavy deps aren't installed.
        from app.environments.cubalibre.envs.env import CubaLibreEnv

        self._env = CubaLibreEnv(verbose=False, manual=True, same_player_control=True)
        self._env.reset()
        return self._env


env_instance = EnvInstance()
