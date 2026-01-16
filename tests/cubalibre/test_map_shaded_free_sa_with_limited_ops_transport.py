import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    OP_TRANSPORT,
    OP_AIR_STRIKE,
)


@unittest.skip("Covered by tests/cubalibre/test_card_10_map.py")
class TestMapShadedFreeSaWithLimitedOpsTransport(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_govt_limited_transport_allows_free_sa_when_map_shaded(self):
        self.env.capabilities.add("MAP_Shaded")

        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.card_action_slot = 1
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10

        dest = 3  # Havana
        src = 2  # La Habana
        self.env.board.spaces[src].pieces[0] = 2

        sierra = 11
        self.env.board.spaces[sierra].pieces[3] = 1

        transport = self.env._limited_ops_action_base + OP_TRANSPORT * self.env.num_spaces + dest
        self.assertEqual(self.env.legal_actions[transport], 1)

        self.env.step(transport)
        self.assertEqual(self.env.phase, 5)  # PHASE_CHOOSE_TARGET_SPACE

        pick_src = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[pick_src], 1)

        self.env.step(pick_src)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        self.assertEqual(self.env.card_action_slot, 1)

        airstrike = self.env._ops_action_base + OP_AIR_STRIKE * self.env.num_spaces + sierra
        self.assertEqual(self.env.legal_actions[airstrike], 1)


if __name__ == "__main__":
    unittest.main()
