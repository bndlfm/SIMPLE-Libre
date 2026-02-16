import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard24VilmaEspin(unittest.TestCase):
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
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

    def _set_card(self, card_id):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def _start_event(self, shaded, acting_player=0):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_sets_sierra_maestra_or_adjacent_to_active_opposition(self):
        # Card 24 (Vilma Espín, Un): Set Sierra Maestra or an adjacent space to Active Opposition.
        self._set_card(24)

        # Sierra Maestra (11)
        self.env.board.spaces[11].alignment = 1  # Support
        self.env.board.spaces[11].support_active = False

        self._start_event(shaded=False, acting_player=0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + 11)
        self.assertEqual(int(self.env.board.spaces[11].alignment), 2)
        self.assertTrue(self.env.board.spaces[11].support_active)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_shaded_removes_all_m26_pieces_from_a_city_other_than_havana(self):
        # Card 24 (Vilma Espín, Sh): Remove all 26July pieces from a City other than Havana.
        self._set_card(24)

        # Santiago (12) is a City and not Havana.
        self.env.board.spaces[12].pieces[2] = 1
        self.env.board.spaces[12].pieces[3] = 1
        self.env.board.spaces[12].pieces[4] = 1

        self._start_event(shaded=True, acting_player=0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + 12)
        self.assertEqual(int(self.env.board.spaces[12].pieces[2]), 0)
        self.assertEqual(int(self.env.board.spaces[12].pieces[3]), 0)
        self.assertEqual(int(self.env.board.spaces[12].pieces[4]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
