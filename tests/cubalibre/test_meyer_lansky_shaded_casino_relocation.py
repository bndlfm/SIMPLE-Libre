import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_MAIN,
)


class TestMeyerLanskyShadedCasinoRelocation(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.closed_casinos = 0
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            sp.update_control()

    def test_meyer_lansky_shaded_casino_relocation_respects_stacking_limits(self):
        d = EVENT_DECK_DATA[38]
        self.env.current_card = Card(38, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 3  # Syndicate
        self.env.players[3].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        src = 3  # Havana
        self.env.board.spaces[src].pieces[10] = 1

        # Destinations for masking assertions.
        ok_two_bases = 2
        too_many_bases = 4
        already_two_casinos = 5
        econ_center = 1

        # ECs are never legal destinations.
        self.env.board.spaces[econ_center].type = 4

        # Cannot exceed 2 casinos.
        self.env.board.spaces[already_two_casinos].pieces[10] = 2

        # Cannot exceed 2 non-casino bases (Govt base + M26 base + DR base).
        self.env.board.spaces[too_many_bases].govt_bases = 2
        self.env.board.spaces[too_many_bases].pieces[4] = 1  # M26 base

        # Exactly 2 non-casino bases is allowed.
        self.env.board.spaces[ok_two_bases].govt_bases = 1
        self.env.board.spaces[ok_two_bases].pieces[4] = 1  # M26 base

        # Ensure other destinations are not ECs.
        self.env.board.spaces[ok_two_bases].type = 1
        self.env.board.spaces[too_many_bases].type = 1
        self.env.board.spaces[already_two_casinos].type = 1

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        # Choose source casino.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_src = self.env._target_space_action_base + src
        self.assertEqual(int(self.env.legal_actions[pick_src]), 1)
        self.env.step(pick_src)

        # Now destination selection should reflect stacking.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_ok = self.env._target_space_action_base + ok_two_bases
        pick_too_many_bases = self.env._target_space_action_base + too_many_bases
        pick_two_casinos = self.env._target_space_action_base + already_two_casinos
        pick_econ = self.env._target_space_action_base + econ_center

        self.assertEqual(int(self.env.legal_actions[pick_ok]), 1)
        self.assertEqual(int(self.env.legal_actions[pick_too_many_bases]), 0)
        self.assertEqual(int(self.env.legal_actions[pick_two_casinos]), 0)
        self.assertEqual(int(self.env.legal_actions[pick_econ]), 0)

    def test_meyer_lansky_shaded_opens_all_closed_casinos_then_allows_relocation(self):
        d = EVENT_DECK_DATA[38]
        self.env.current_card = Card(38, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 3  # Syndicate
        self.env.players[3].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        src = 3  # Havana (City)
        dest_ok = 2  # La Habana (Province)
        econ_center = 1  # Cigar EC (Econ center)

        # Start with one open casino + one closed casino to prove closed -> open.
        self.env.board.spaces[src].pieces[10] = 1
        self.env.board.spaces[src].closed_casinos = 1

        # Ensure there is at least one legal relocation destination.
        self.env.board.spaces[dest_ok].pieces[10] = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        # Closed casinos should be opened immediately.
        self.assertEqual(int(self.env.board.spaces[src].closed_casinos), 0)
        self.assertEqual(int(self.env.board.spaces[src].pieces[10]), 2)

        # Now should be choosing a source casino.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_src = self.env._target_space_action_base + src
        self.assertEqual(int(self.env.legal_actions[pick_src]), 1)
        self.env.step(pick_src)

        # Choosing destination.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # Econ centers are never legal destinations for Casinos.
        pick_econ = self.env._target_space_action_base + econ_center
        self.assertEqual(int(self.env.legal_actions[pick_econ]), 0)

        # A normal destination should be legal.
        pick_dest_ok = self.env._target_space_action_base + dest_ok
        self.assertEqual(int(self.env.legal_actions[pick_dest_ok]), 1)

        self.env.step(pick_dest_ok)

        self.assertEqual(int(self.env.board.spaces[src].pieces[10]), 1)
        self.assertEqual(int(self.env.board.spaces[dest_ok].pieces[10]), 1)

        # Should prompt whether to continue moving more Casinos if possible.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        # Stop.
        stop = self.env._event_option_action_base + 0
        self.assertEqual(int(self.env.legal_actions[stop]), 1)
        self.env.step(stop)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
