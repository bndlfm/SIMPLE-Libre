"""Regression test: an ineligible player at PHASE_CHOOSE_MAIN must be
auto-skipped per COIN rules.  They must NOT be forced to PASS (which would
award free resources), and they must not produce an all-zeros action mask
that hangs the selfplay loop.

Root cause: legal_actions returned np.zeros() when the current player was
ineligible at PHASE_CHOOSE_MAIN.  The opponent model picked random illegal
actions forever.  Fix: action_masks() auto-advances the turn pointer past
ineligible players, matching the physical board game's skip rules.
"""
import unittest
import numpy as np

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_PASS,
    PHASE_CHOOSE_MAIN,
)


class TestIneligiblePlayerAutoSkip(unittest.TestCase):
    """Verify that ineligible factions are auto-skipped without gaining
    resources, matching COIN 2018 rules."""

    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=42)

        # Clear the board
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
        """Force the current card to Meyer Lansky (card 38)."""
        d = EVENT_DECK_DATA[38]
        self.env.current_card = Card(
            38, d["name"], d["order"], d["unshaded"], d["shaded"]
        )

    def _setup_repro_board(self):
        """Set up the exact board state from the repro log."""
        spaces = self.env.board.spaces
        # La Habana: 3 Troops
        spaces[2].pieces[0] = 3
        # Havana: 2 Troops, 6 M26 Underground
        spaces[3].pieces[0] = 2
        spaces[3].pieces[2] = 6
        # Camaguey City: 1 M26 Underground
        spaces[7].pieces[2] = 1
        # Sierra Maestra: 1 M26 Underground, 1 Syndicate Underground
        spaces[9].pieces[2] = 1
        spaces[9].pieces[8] = 1
        # Santiago De Cuba: 1 Troop
        spaces[10].pieces[0] = 1
        for sp in spaces:
            sp.update_control()

    def test_action_masks_skips_ineligible_player(self):
        """action_masks() must auto-skip an ineligible player, returning a
        non-zero mask for the next eligible player."""
        self._set_meyer_lansky_card()
        self._setup_repro_board()

        # Make GOVT the current player but ineligible
        self.env.current_player_num = 0
        self.env.players[0].eligible = False
        self.env.players[0].resources = 35
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        masks = self.env.action_masks()
        self.assertTrue(
            masks.any(),
            "action_masks() must not return all zeros — should have auto-skipped "
            "the ineligible player"
        )
        # The current player should have changed away from GOVT
        self.assertNotEqual(
            self.env.current_player_num, 0,
            "After auto-skip, current_player_num should not be GOVT"
        )

    def test_ineligible_player_does_not_gain_resources(self):
        """Per COIN rules, ineligible players are skipped — they do NOT gain
        resources (unlike PASS which gives +3/+1)."""
        self._set_meyer_lansky_card()
        self._setup_repro_board()

        self.env.current_player_num = 0
        self.env.players[0].eligible = False
        self.env.players[0].resources = 35
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        # action_masks() triggers the auto-skip
        self.env.action_masks()

        # GOVT should NOT have gained resources (PASS would give +3)
        self.assertEqual(
            self.env.players[0].resources, 35,
            "Ineligible player must NOT gain resources — they are skipped, not passing"
        )

    def test_multiple_ineligible_players_auto_skip(self):
        """If multiple players are ineligible, the game should skip all of
        them until it finds an eligible player."""
        self._set_meyer_lansky_card()
        self._setup_repro_board()

        # Make GOVT and M26 ineligible
        self.env.current_player_num = 0
        self.env.players[0].eligible = False
        self.env.players[1].eligible = False
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env._card_order_index = 0

        masks = self.env.action_masks()
        self.assertTrue(masks.any(), "Mask should not be all zeros after auto-skip")

        # Current player should be neither GOVT (0) nor M26 (1)
        self.assertNotIn(
            self.env.current_player_num, [0, 1],
            "Should have skipped both ineligible players"
        )


if __name__ == "__main__":
    unittest.main()
