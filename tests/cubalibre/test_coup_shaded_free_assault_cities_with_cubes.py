import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    PHASE_CHOOSE_MAIN,
)


class TestCoupShadedFreeAssaultCitiesWithCubes(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    @unittest.skip("Covered by tests/cubalibre/test_card_9_coup.py")
    def test_coup_shaded_activates_and_assaults_dr_in_cities_with_cubes(self):
        d = EVENT_DECK_DATA[9]
        self.env.current_card = Card(9, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env._card_order_index = 0
        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True

        havana = 3
        self.env.board.spaces[havana].pieces[0] = 2  # Govt troops
        self.env.board.spaces[havana].pieces[5] = 2  # DR underground guerrillas

        santiago = 5
        self.env.board.spaces[santiago].pieces[5] = 2  # DR underground guerrillas

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.board.spaces[havana].pieces[5], 0)
        self.assertEqual(self.env.board.spaces[havana].pieces[6], 0)

        self.assertEqual(self.env.board.spaces[santiago].pieces[5], 2)
        self.assertEqual(self.env.board.spaces[santiago].pieces[6], 0)


if __name__ == "__main__":
    unittest.main()
