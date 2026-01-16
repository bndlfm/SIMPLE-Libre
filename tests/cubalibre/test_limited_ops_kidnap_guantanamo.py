import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    OP_TERROR_M26,
)


class TestLimitedOpsKidnapGuantanamo(unittest.TestCase):
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

    def test_kidnap_not_in_limited_ops_even_with_guantanamo(self):
        self.env.capabilities.add("Guantanamo_Unshaded")
        self.env.current_player_num = 1  # M26
        self.env.players[1].resources = 5
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"

        sierra = 11
        self.env.board.spaces[sierra].pieces[2] = 1

        action = self.env._limited_ops_action_base + OP_TERROR_M26 * self.env.num_spaces + sierra
        self.assertEqual(self.env.legal_actions[action], 1)

        kidnap = self.env._limited_ops_action_base + (16 * self.env.num_spaces) + sierra
        self.assertEqual(self.env.legal_actions[kidnap], 0)


if __name__ == "__main__":
    unittest.main()
