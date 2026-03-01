"""Test that Meyer Lansky (Un) fizzles when no space has cash to transfer.

When the event is chosen but no space qualifies (no cash or no valid transfer
between holders), the event should fizzle immediately without entering the
SPACE selection stage.
"""
import unittest
import numpy as np

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    MAIN_PASS,
    EVENT_UNSHADED,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestMeyerLanskyFizzle(unittest.TestCase):
    """Meyer Lansky (Un) should fizzle when no space has cash to transfer."""

    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=42)

        # Clear the board — no cash anywhere
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.closed_casinos = 0
            sp.cash[:] = 0
            sp.cash_holders[:] = 0
            sp.update_control()

    def _set_meyer_lansky_card(self):
        d = EVENT_DECK_DATA[38]
        self.env.current_card = Card(
            38, d["name"], d["order"], d["unshaded"], d["shaded"]
        )

    def test_fizzle_when_no_cash(self):
        """Event fizzles and returns to PHASE_CHOOSE_MAIN when no cash exists."""
        self._set_meyer_lansky_card()

        # Put some pieces but NO cash
        self.env.board.spaces[3].pieces[0] = 2  # Troops
        self.env.board.spaces[3].pieces[2] = 3  # M26
        self.env.board.spaces[3].update_control()

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        # Choose Event → Unshaded
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Event should have fizzled — phase should NOT be PHASE_CHOOSE_TARGET_SPACE
        self.assertNotEqual(
            self.env.phase, PHASE_CHOOSE_TARGET_SPACE,
            "Meyer Lansky (Un) should fizzle when no space has cash to transfer"
        )

    def test_no_all_zeros_mask_after_fizzle(self):
        """After fizzle, action_masks must not be all zeros."""
        self._set_meyer_lansky_card()

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        # Choose Event → Unshaded (no cash on empty board = fizzle)
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        masks = self.env.action_masks()
        self.assertTrue(masks.any(), "Mask must not be all zeros after event fizzle")


if __name__ == "__main__":
    unittest.main()
