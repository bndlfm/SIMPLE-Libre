import random
import unittest

import numpy as np

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_MAIN,
)


class TestCashHolderRemoval(unittest.TestCase):
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

    def test_cash_transfers_to_other_same_faction_piece_on_removal(self):
        sp = self.env.board.spaces[3]  # Havana

        # M26 Underground holds cash, M26 Active remains.
        sp.pieces[2] = 1
        sp.pieces[3] = 1
        self.env._add_cash_marker(sp, 1, preferred_idx=2)

        self.env.board.remove_piece(3, 1, 0)  # Remove M26 Underground

        self.env.phase = PHASE_CHOOSE_MAIN
        choice = self.env._target_piece_action_base + 3
        self.env.step(choice)

        self.assertEqual(int(sp.cash[1]), 1)
        self.assertEqual(int(sp.cash_holders[3]), 1)
        self.assertEqual(int(sp.cash_holders[2]), 0)

    def test_cash_removed_when_no_pieces_remain(self):
        sp = self.env.board.spaces[3]  # Havana

        sp.pieces[2] = 1
        self.env._add_cash_marker(sp, 1, preferred_idx=2)

        self.env.board.remove_piece(3, 1, 0)

        self.env.phase = PHASE_CHOOSE_MAIN
        remove_choice = self.env._target_piece_action_base + (self.env._target_piece_action_count - 1)
        self.env.step(remove_choice)

        self.assertEqual(int(sp.cash[1]), 0)
        self.assertEqual(int(sp.cash_holders[2]), 0)

    def test_cash_transfers_to_other_faction_piece_when_needed(self):
        sp = self.env.board.spaces[3]  # Havana

        # M26 holds cash, only a Govt piece remains to receive it.
        sp.pieces[2] = 1
        sp.pieces[0] = 1
        self.env._add_cash_marker(sp, 1, preferred_idx=2)

        self.env.board.remove_piece(3, 1, 0)

        self.env.phase = PHASE_CHOOSE_MAIN
        choice = self.env._target_piece_action_base + 0
        self.env.step(choice)

        self.assertEqual(int(sp.cash[1]), 0)
        self.assertEqual(int(sp.cash[0]), 1)
        self.assertEqual(int(sp.cash_holders[0]), 1)


if __name__ == "__main__":
    unittest.main()
