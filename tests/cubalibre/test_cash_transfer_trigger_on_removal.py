import random
import unittest

import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_TARGET_PIECE


class TestCashTransferTriggerOnRemoval(unittest.TestCase):
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

    def test_assault_removal_triggers_cash_transfer_choice(self):
        s_id = 3  # Havana
        sp = self.env.board.spaces[s_id]

        # Govt troops assault; M26 has 1 active guerrilla holding cash.
        sp.pieces[0] = 2  # Govt Troops
        sp.pieces[3] = 1  # M26 Active
        self.env._add_cash_marker(sp, 1, preferred_idx=3)

        self.env._op_assault_impl(s_id)

        self.assertTrue(self.env._cash_transfer_waiting)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_PIECE)
        self.assertEqual(int(sp.cash_holders[3]), 1)

        # Choose to remove the cash.
        remove_choice = self.env._target_piece_action_base + (self.env._target_piece_action_count - 1)
        self.env.step(remove_choice)

        self.assertEqual(int(sp.cash_holders[3]), 0)
        self.assertEqual(int(sp.cash[1]), 0)


if __name__ == "__main__":
    unittest.main()
