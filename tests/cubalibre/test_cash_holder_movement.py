import random
import unittest

import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_TARGET_SPACE


class TestCashHolderMovement(unittest.TestCase):
    def setUp(self):
        self._random_state = random.getstate()
        self._np_random_state = np.random.get_state()
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.closed_casinos = 0
            sp.cash[:] = 0
            sp.cash_holders[:] = 0
            sp.update_control()

    def tearDown(self):
        random.setstate(self._random_state)
        np.random.set_state(self._np_random_state)

    def test_transport_moves_cash_with_troops(self):
        src = 2  # La Habana
        dest = 3  # Havana (Transport target)

        sp_src = self.env.board.spaces[src]
        sp_dest = self.env.board.spaces[dest]
        sp_src.pieces[0] = 2  # Govt Troops
        sp_dest.pieces[0] = 1
        self.env._add_cash_marker(sp_src, 0, preferred_idx=0)

        self.env.op_transport(dest)

        self.assertEqual(int(sp_src.cash[0]), 0)
        self.assertEqual(int(sp_dest.cash[0]), 1)
        self.assertEqual(int(sp_dest.cash_holders[0]), 1)

    def test_transport_target_op_moves_cash(self):
        src = 2  # La Habana
        dest = 3  # Havana

        sp_src = self.env.board.spaces[src]
        sp_dest = self.env.board.spaces[dest]
        sp_src.pieces[0] = 1  # Govt Troops
        sp_dest.pieces[0] = 1
        self.env._add_cash_marker(sp_src, 0, preferred_idx=0)

        self.env.current_player_num = 0
        self.env.phase = PHASE_CHOOSE_TARGET_SPACE
        self.env._pending_op_target = {"op": "TRANSPORT_SRC", "dest": dest}

        action = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[action], 1)
        self.env.step(action)

        self.assertEqual(int(sp_src.pieces[0]), 0)
        self.assertEqual(int(sp_dest.pieces[0]), 2)
        self.assertEqual(int(sp_src.cash_holders[0]), 0)
        self.assertEqual(int(sp_dest.cash_holders[0]), 1)

    def test_march_moves_cash_and_flips_to_active(self):
        self.env.current_player_num = 1  # M26
        src = 2  # La Habana
        dest = 3  # Havana (City => flips to Active)

        sp_src = self.env.board.spaces[src]
        sp_dest = self.env.board.spaces[dest]
        sp_src.pieces[2] = 1  # M26 Underground
        self.env._add_cash_marker(sp_src, 1, preferred_idx=2)

        self.env._op_march_insurgent(dest, 2, 3)

        self.assertEqual(int(sp_src.cash[1]), 0)
        self.assertEqual(int(sp_dest.cash[1]), 1)
        self.assertEqual(int(sp_dest.cash_holders[3]), 1)
        self.assertEqual(int(sp_dest.cash_holders[2]), 0)

    def test_sweep_reveal_moves_cash_to_active(self):
        s_id = 8  # Camaguey City (City)
        sp = self.env.board.spaces[s_id]
        sp.pieces[2] = 2  # M26 Underground
        self.env._add_cash_marker(sp, 1, preferred_idx=2)

        self.env._op_sweep_impl(s_id)

        self.assertEqual(int(sp.cash[1]), 1)
        self.assertEqual(int(sp.cash_holders[3]), 1)
        self.assertEqual(int(sp.cash_holders[2]), 0)


if __name__ == "__main__":
    unittest.main()
