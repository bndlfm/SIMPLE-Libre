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


class TestCard23RadioRebelde(unittest.TestCase):
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

    def test_unshaded_requires_two_distinct_provinces(self):
        # Card 23 (Radio Rebelde, Un): Shift 2 Provinces each 1 level toward Active Opposition.
        # Must be 2 distinct Provinces.
        self._set_card(23)

        # Use two Provinces (type 1/2/3) not a City/Econ Center.
        # La Habana (2) and Matanzas (4)
        self.env.board.spaces[2].alignment = 1
        self.env.board.spaces[2].support_active = False
        self.env.board.spaces[4].alignment = 1
        self.env.board.spaces[4].support_active = False

        self._start_event(shaded=False, acting_player=0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_2 = self.env._target_space_action_base + 2
        pick_4 = self.env._target_space_action_base + 4
        self.assertEqual(int(self.env.legal_actions[pick_2]), 1)

        self.env.step(pick_2)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(int(self.env.legal_actions[pick_2]), 0)

        self.assertEqual(int(self.env.legal_actions[pick_4]), 1)
        self.env.step(pick_4)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_shaded_removes_m26_base_from_province(self):
        # Card 23 (Radio Rebelde, Sh): Remove a 26July Base from a Province.
        self._set_card(23)

        # Pinar Del Rio (0) is a Province.
        self.env.board.spaces[0].pieces[4] = 1

        self._start_event(shaded=True, acting_player=0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(int(self.env.board.spaces[0].pieces[4]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
