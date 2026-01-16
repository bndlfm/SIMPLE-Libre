import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    OP_MARCH_DR,
)


class TestLimitedOpsMorganMarchRange(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

    def test_limited_ops_morgan_allows_two_step_march(self):
        self.env.capabilities.add("Morgan_Unshaded")
        self.env.current_player_num = 2  # DR
        self.env.players[2].resources = 5
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"

        dest = 3  # Havana
        src = 0  # Pinar Del Rio (2 steps from Havana via La Habana)
        self.env.board.spaces[src].pieces[5] = 1

        action = self.env._limited_ops_action_base + OP_MARCH_DR * self.env.num_spaces + dest
        self.assertEqual(self.env.legal_actions[action], 1)

    def test_limited_ops_without_morgan_requires_adjacent(self):
        self.env.current_player_num = 2  # DR
        self.env.players[2].resources = 5
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"

        dest = 3  # Havana
        src = 0  # Pinar Del Rio (not adjacent)
        self.env.board.spaces[src].pieces[5] = 1

        action = self.env._limited_ops_action_base + OP_MARCH_DR * self.env.num_spaces + dest
        self.assertEqual(self.env.legal_actions[action], 0)


if __name__ == "__main__":
    unittest.main()
