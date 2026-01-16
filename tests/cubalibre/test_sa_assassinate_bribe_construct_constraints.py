import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    OP_ASSASSINATE_DR,
    OP_BRIBE_SYN,
    OP_CONSTRUCT_SYN,
)


class TestSaAssassinateBribeConstructConstraints(unittest.TestCase):
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

    def test_assassinate_requires_city_or_econ_and_govt(self):
        self.env.current_player_num = 2  # DR
        self.env.players[2].resources = 5
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

        city = 3  # Havana
        self.env.board.spaces[city].pieces[5] = 1
        self.env.board.spaces[city].pieces[0] = 1

        action = self.env._ops_action_base + OP_ASSASSINATE_DR * self.env.num_spaces + city
        self.assertEqual(self.env.legal_actions[action], 1)

        province = 0
        self.env.board.spaces[province].pieces[5] = 1
        self.env.board.spaces[province].pieces[0] = 1

        action2 = self.env._ops_action_base + OP_ASSASSINATE_DR * self.env.num_spaces + province
        self.assertEqual(self.env.legal_actions[action2], 0)

    def test_bribe_and_construct_constraints(self):
        self.env.current_player_num = 3  # Syndicate
        self.env.players[3].resources = 5
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

        city = 3
        self.env.board.spaces[city].pieces[8] = 1

        bribe = self.env._ops_action_base + OP_BRIBE_SYN * self.env.num_spaces + city
        self.assertEqual(self.env.legal_actions[bribe], 1)

        construct = self.env._ops_action_base + OP_CONSTRUCT_SYN * self.env.num_spaces + city
        self.env.players[3].available_bases = 0
        self.assertEqual(self.env.legal_actions[construct], 0)

        self.env.players[3].available_bases = 1
        self.assertEqual(self.env.legal_actions[construct], 1)


if __name__ == "__main__":
    unittest.main()
