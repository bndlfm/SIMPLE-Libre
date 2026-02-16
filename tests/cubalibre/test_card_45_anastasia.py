import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_MAIN,
)


class TestCard45Anastasia(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        d = EVENT_DECK_DATA[45]
        self.env.current_card = Card(45, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        for p in self.env.players:
            p.eligible = True

    def test_anastasia_unshaded_closes_all_havana_casinos_and_syn_minus_5(self):
        havana = self.env.board.spaces[3]
        havana.pieces[10] = 2
        havana.closed_casinos = 1
        havana.update_control()

        self.env.players[3].resources = 3

        self.env.current_player_num = 3
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(int(havana.pieces[10]), 0)
        self.assertEqual(int(havana.closed_casinos), 3)
        self.assertEqual(int(self.env.players[3].resources), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_anastasia_shaded_syn_plus_10_capped_at_49(self):
        self.env.players[3].resources = 45

        self.env.current_player_num = 3
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(int(self.env.players[3].resources), 49)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
