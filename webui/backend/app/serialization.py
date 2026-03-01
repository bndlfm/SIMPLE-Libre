from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np


def _sparse_legal_actions(mask: np.ndarray) -> List[int]:
    if mask is None:
        return []
    mask = np.asarray(mask)
    return [int(i) for i in np.nonzero(mask)[0].tolist()]


def serialize_env(env, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # Defensive: env is a CubaLibreEnv, but keep this function side-effect free.

    # Ensure cash counts are refreshed.
    for sp in getattr(env.board, "spaces", []):
        if hasattr(env, "_refresh_space_cash_counts"):
            env._refresh_space_cash_counts(sp)

    current_card = getattr(env, "current_card", None)
    next_card = getattr(env, "next_card", None)

    def card_to_json(card) -> Optional[Dict[str, Any]]:
        if card is None:
            return None
        return {
            "id": int(card.id),
            "name": str(card.name),
            "is_propaganda": bool(getattr(card, "is_propaganda", False)),
            "faction_order": list(getattr(card, "faction_order", [])),
            "unshaded": str(getattr(card, "text_unshaded", "")),
            "shaded": str(getattr(card, "text_shaded", "")),
        }

    spaces: List[Dict[str, Any]] = []
    for sp in env.board.spaces:
        pieces = np.asarray(sp.pieces).astype(int).tolist()
        cash = np.asarray(getattr(sp, "cash", np.zeros(4))).astype(int).tolist()
        spaces.append(
            {
                "id": int(sp.id),
                "name": str(sp.name),
                "type": int(sp.type),
                "population": int(sp.population),
                "econ": int(sp.econ_value),
                "adj": [int(x) for x in sp.adj_ids],
                "alignment": int(sp.alignment),
                "support_active": bool(getattr(sp, "support_active", False)),
                "terror": int(sp.terror),
                "sabotage": bool(getattr(sp, "sabotage", False)),
                "controlled_by": int(getattr(sp, "controlled_by", 0)),
                "pieces_raw": pieces,
                "closed_casinos": int(getattr(sp, "closed_casinos", 0)),
                "cash": {
                    "govt": int(cash[0]),
                    "m26": int(cash[1]),
                    "dr": int(cash[2]),
                    "syn": int(cash[3]),
                },
            }
        )

    players = []
    for p in getattr(env, "players", []):
        players.append(
            {
                "id": int(p.id),
                "name": str(p.name),
                "resources": int(p.resources),
                "points": int(getattr(p, "points", 0)),
                "eligible": bool(p.eligible),
                "available_forces": [int(x) for x in getattr(p, "available_forces", [])],
                "available_bases": int(getattr(p, "available_bases", 0)),
            }
        )

    legal_ones = _sparse_legal_actions(getattr(env, "legal_actions", None))

    action_ranges = {
        "main": {
            "base": int(getattr(env, "_main_action_base", 0)),
            "count": int(getattr(env, "_main_action_count", 0)),
        },
        "event_side": {
            "base": int(getattr(env, "_event_side_base", 0)),
            "count": int(getattr(env, "_event_side_count", 0)),
        },
        "ops": {
            "base": int(getattr(env, "_ops_action_base", 0)),
            "count": int(getattr(env, "_ops_action_count", 0)),
        },
        "limited_main": {
            "id": int(getattr(env, "_limited_main_action_id", 0)),
        },
        "limited_ops": {
            "base": int(getattr(env, "_limited_ops_action_base", 0)),
            "count": int(getattr(env, "_limited_ops_action_count", 0)),
        },
        "target_space": {
            "base": int(getattr(env, "_target_space_action_base", 0)),
            "count": int(getattr(env, "_target_space_action_count", 0)),
        },
        "target_faction": {
            "base": int(getattr(env, "_target_faction_action_base", 0)),
            "count": int(getattr(env, "_target_faction_action_count", 0)),
        },
        "event_option": {
            "base": int(getattr(env, "_event_option_action_base", 0)),
            "count": int(getattr(env, "_event_option_action_count", 0)),
        },
        "target_piece": {
            "base": int(getattr(env, "_target_piece_action_base", 0)),
            "count": int(getattr(env, "_target_piece_action_count", 0)),
        },
    }

    payload: Dict[str, Any] = {
        "game": "cubalibre",
        "done": bool(getattr(env, "done", False)),
        "phase": int(getattr(env, "phase", 0)),
        "current_player": int(getattr(env, "current_player_num", 0)),
        "players": players,
        "tracks": {
            "aid": int(getattr(env, "aid", 0)),
            "us_alliance": int(getattr(env, "us_alliance", 0)),
            "total_support": int(getattr(env, "total_support_track", 0)),
            "opposition_plus_bases": int(getattr(env, "opposition_plus_bases_track", 0)),
            "dr_pop_plus_bases": int(getattr(env, "dr_pop_plus_bases_track", 0)),
            "open_casinos": int(getattr(env, "open_casinos_track", 0)),
            "propaganda_cards_played": int(getattr(env, "propaganda_cards_played", 0)),
        },
        "card": {
            "current": card_to_json(current_card),
            "next": card_to_json(next_card),
        },
        "spaces": spaces,
        "action_ranges": action_ranges,
        "legal_actions": {
            "n": int(getattr(env.action_space, "n", 0)),
            "ones": legal_ones,
        },
        "pending": {
            "faction": getattr(env, "_pending_event_faction", None),
            "option": getattr(env, "_pending_event_option", None),
            "target": getattr(env, "_pending_event_target", None) or getattr(env, "_pending_op_target", None),
        },
    }

    payload["meta"] = metadata or {}

    return payload
