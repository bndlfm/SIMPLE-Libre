import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    MAIN_OPS,
    OP_TERROR_M26,
    OP_KIDNAP_M26,
    OP_CONSTRUCT_SYN,
    OP_RALLY_SYN
)

class TestEdgeCasesSpecialActivities(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash[:] = 0
            sp.cash_holders[:] = 0
            sp.update_control()

    def test_kidnap_requires_terror(self):
        s_id = 3 # Havana City
        sp = self.env.board.spaces[s_id]

        sp.pieces[2] = 2 # M26
        sp.pieces[1] = 1 # Police

        self.env.current_player_num = 1 # M26
        self.env.players[1].resources = 5
        self.env.players[0].resources = 5

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.step(self.env._main_action_base + MAIN_OPS)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        self.env.step(self.env._ops_action_base + OP_TERROR_M26 * self.env.num_spaces + s_id)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        legal = self.env.legal_actions
        kidnap_action = self.env._ops_action_base + OP_KIDNAP_M26 * self.env.num_spaces + s_id
        self.assertEqual(legal[kidnap_action], 1)

        s_id_2 = 0
        sp_2 = self.env.board.spaces[s_id_2]
        sp_2.pieces[2] = 2
        sp_2.pieces[10] = 1

        kidnap_action_2 = self.env._ops_action_base + OP_KIDNAP_M26 * self.env.num_spaces + s_id_2
        self.env.step(kidnap_action)

        self.assertEqual(self.env.players[1].resources, 6)

    def test_launder_disallows_construct(self):
        s_id = 3
        sp = self.env.board.spaces[s_id]

        sp.pieces[8] = 1
        self.env._add_cash_marker(sp, 3, preferred_idx=8)

        self.env.current_player_num = 3
        self.env.players[3].resources = 5
        self.env.players[3].available_bases = 10

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.step(self.env._main_action_base + MAIN_OPS)

        self.env.step(self.env._ops_action_base + OP_RALLY_SYN * self.env.num_spaces + s_id)

        self.env.step(self.env._main_action_base + 0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.assertTrue(self.env._pending_launder)

        self.env.step(self.env._target_faction_action_base + 3)
        self.env.step(self.env._target_space_action_base + s_id)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_LIMITED_OP_ACTION)

        legal = self.env.legal_actions
        construct_action = self.env._limited_ops_action_base + OP_CONSTRUCT_SYN * self.env.num_spaces + s_id
        self.assertEqual(legal[construct_action], 0)

        rally_action = self.env._limited_ops_action_base + OP_RALLY_SYN * self.env.num_spaces + s_id
        self.assertEqual(legal[rally_action], 1)


if __name__ == '__main__':
    unittest.main()
