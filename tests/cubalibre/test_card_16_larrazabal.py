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


class TestCard16Larrazabal(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.update_control()

    def test_larrazabal_unshaded_places_m26_base_where_m26_piece_exists(self):
        d = EVENT_DECK_DATA[16]
        self.env.current_card = Card(16, d["name"], d["order"], d["unshaded"], d["shaded"])

        target = 3
        self.env.board.spaces[target].pieces[2] = 1  # M26 Underground guerrilla
        self.env.players[1].available_bases = 10

        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(int(self.env.legal_actions[self.env._target_space_action_base + target]), 1)

        self.env.step(self.env._target_space_action_base + target)

        self.assertEqual(int(self.env.board.spaces[target].pieces[4]), 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_larrazabal_shaded_removes_m26_base_and_reduces_m26_resources_by_3(self):
        d = EVENT_DECK_DATA[16]
        self.env.current_card = Card(16, d["name"], d["order"], d["unshaded"], d["shaded"])

        target = 5
        self.env.board.spaces[target].pieces[4] = 1  # M26 Base
        self.env.players[1].resources = 2

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(int(self.env.legal_actions[self.env._target_space_action_base + target]), 1)

        self.env.step(self.env._target_space_action_base + target)

        self.assertEqual(int(self.env.board.spaces[target].pieces[4]), 0)
        self.assertEqual(int(self.env.players[1].resources), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
