import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_LIMITED_OP_ACTION


class TestLimitedOpsResourceCosts(unittest.TestCase):
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

    def test_govt_limited_ops_blocked_with_insufficient_resources(self):
        self.env.current_player_num = 0
        self.env.players[0].resources = 0
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"

        mask = self.env.legal_actions
        limited = mask[self.env._limited_ops_action_base:self.env._limited_ops_action_base + self.env._limited_ops_action_count]
        self.assertEqual(int(limited.sum()), 0)

    def test_insurgent_limited_ops_blocked_with_insufficient_resources(self):
        self.env.current_player_num = 1
        self.env.players[1].resources = 0
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"

        mask = self.env.legal_actions
        limited = mask[self.env._limited_ops_action_base:self.env._limited_ops_action_base + self.env._limited_ops_action_count]
        self.assertEqual(int(limited.sum()), 0)


if __name__ == "__main__":
    unittest.main()
