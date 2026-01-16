import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_OP_ACTION,
    OP_TERROR_M26,
)


@unittest.skip("Covered by tests/cubalibre/test_card_18_pact_of_caracas.py")
class TestPactOfCaracasMutualTransfers(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash_holders[:] = 0
            sp.refresh_cash_counts()
            sp.update_control()

    def test_pact_blocks_terror_when_not_same_player(self):
        env = CubaLibreEnv(verbose=False, manual=False, same_player_control=False)
        env.reset(seed=123)
        for sp in env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash_holders[:] = 0
            sp.refresh_cash_counts()
            sp.update_control()

        env.capabilities.add("PactOfCaracas_Unshaded")
        env.current_player_num = 1
        env.players[1].resources = 10
        env.phase = PHASE_CHOOSE_OP_ACTION
        env.card_action_slot = 0

        space_id = 0
        env.board.spaces[space_id].pieces[2] = 1

        action = env._ops_action_base + OP_TERROR_M26 * env.num_spaces + space_id
        self.assertEqual(env.legal_actions[action], 0)

    def test_pact_allows_terror_when_same_player(self):
        self.env.capabilities.add("PactOfCaracas_Unshaded")
        self.env.current_player_num = 1
        self.env.players[1].resources = 10
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        space_id = 0
        self.env.board.spaces[space_id].pieces[2] = 1

        action = self.env._ops_action_base + OP_TERROR_M26 * self.env.num_spaces + space_id
        self.assertEqual(self.env.legal_actions[action], 1)

        self.env.step(action)
        self.assertEqual(int(self.env.board.spaces[space_id].terror), 1)


if __name__ == "__main__":
    unittest.main()
