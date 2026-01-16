import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    EVENT_UNSHADED,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestFatButcherAgentChoices(unittest.TestCase):
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
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

        d = EVENT_DECK_DATA[41]
        self.env.current_card = Card(41, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 0
        self.env.card_action_slot = 0
        self.env.phase = PHASE_CHOOSE_MAIN

    def test_fat_butcher_unshaded_closes_selected_casino(self):
        casino_sp = self.env.board.spaces[5]
        casino_sp.pieces[10] = 1
        self.env.aid = 10

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + casino_sp.id)

        self.assertEqual(int(casino_sp.pieces[10]), 0)
        self.assertEqual(int(casino_sp.closed_casinos), 1)
        self.assertEqual(int(self.env.aid), 10)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_fat_butcher_unshaded_only_allows_aid_loss_when_no_casinos(self):
        self.env.aid = 10

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        aid_option = self.env._event_option_action_base + 1
        close_option = self.env._event_option_action_base + 0
        self.assertEqual(int(self.env.legal_actions[close_option]), 0)
        self.assertEqual(int(self.env.legal_actions[aid_option]), 1)

        self.env.step(aid_option)

        self.assertEqual(int(self.env.aid), 2)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_fat_butcher_shaded_ambush_then_open_closed_casino(self):
        ambush_sp = self.env.board.spaces[3]
        ambush_sp.pieces[0] = 1
        ambush_sp.pieces[8] = 1
        closed_sp = self.env.board.spaces[0]
        closed_sp.closed_casinos = 1

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + ambush_sp.id)

        self.assertEqual(int(ambush_sp.pieces[0]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + closed_sp.id)

        self.assertEqual(int(closed_sp.closed_casinos), 0)
        self.assertEqual(int(closed_sp.pieces[10]), 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
