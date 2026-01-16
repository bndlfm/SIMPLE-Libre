import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    OP_TERROR_M26,
)


class TestLimitedOpsPactBlocksTerror(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False, same_player_control=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

    def test_pact_blocks_limited_ops_terror(self):
        self.env.capabilities.add("PactOfCaracas_Unshaded")
        self.env.current_player_num = 1  # M26
        self.env.players[1].resources = 5
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"

        space_id = 0
        self.env.board.spaces[space_id].pieces[2] = 1

        action = self.env._limited_ops_action_base + OP_TERROR_M26 * self.env.num_spaces + space_id
        self.assertEqual(self.env.legal_actions[action], 0)


if __name__ == "__main__":
    unittest.main()
