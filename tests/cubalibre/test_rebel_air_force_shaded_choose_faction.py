import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    PHASE_CHOOSE_TARGET_FACTION,
)


class TestRebelAirForceShadedChooseFaction(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    @unittest.skip("Covered by tests/cubalibre/test_card_44_rebel_air_force.py")
    def test_rebel_air_force_shaded_requires_faction_choice_and_transfers(self):
        d = EVENT_DECK_DATA[44]
        self.env.current_card = Card(44, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        self.env.players[0].resources = 10
        self.env.players[1].resources = 6
        self.env.players[2].resources = 0
        self.env.players[3].resources = 0

        # Make die deterministic.
        self.env._roll_die = lambda: 4

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        choose_m26 = self.env._target_faction_action_base + 1
        self.assertEqual(self.env.legal_actions[choose_m26], 1)

        self.env.step(choose_m26)

        self.assertEqual(self.env.players[0].resources, 10)
        self.assertEqual(self.env.players[1].resources, 2)
        self.assertEqual(self.env.players[3].resources, 4)


if __name__ == "__main__":
    unittest.main()
