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


class TestCard15ComeComrades(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.update_control()

    def test_come_comrades_unshaded_three_placements(self):
        # Card 15 (Un): Place 3 M26 Guerrillas anywhere.
        d = EVENT_DECK_DATA[15]
        self.env.current_card = Card(15, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 1
        self.env.players[1].eligible = True

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        for i, s_id in enumerate([0, 1, 2]):
            self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
            self.assertEqual(int(self.env._pending_event_target["count"]), i)
            self.env.step(self.env._target_space_action_base + s_id)
            self.assertEqual(int(self.env.board.spaces[s_id].pieces[2]), 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_come_comrades_shaded_adds_govt_resources_and_aid(self):
        # Card 15 (Sh): Add min(Aid, 10) to Govt resources. Then Aid +5.
        d = EVENT_DECK_DATA[15]
        self.env.current_card = Card(15, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 0
        self.env.players[0].eligible = True

        self.env.aid = 7
        self.env.players[0].resources = 20

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(int(self.env.players[0].resources), 27)
        self.assertEqual(int(self.env.aid), 12)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
