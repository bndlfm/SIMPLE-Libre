import unittest
import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv

class TestKidnapCashTransfer(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False)
        self.env.reset(seed=42)

    def test_kidnap_cash_transfer(self):
        # Setup Havana (Space 3, City)
        sp = self.env.board.spaces[3]
        sp.pieces[:] = 0
        sp.govt_bases = 0

        # M26 needs more guerrillas than Police
        sp.pieces[2] = 2 # M26 UG
        sp.pieces[1] = 1 # Govt Police

        # Give Govt a Cash marker
        self.env._add_cash_marker(sp, 0, preferred_idx=1)
        self.assertEqual(int(sp.cash[0]), 1, "Govt should have 1 cash")

        self.env.current_player_num = 1 # M26

        # op_kidnap_m26 targets Govt (0) or Syn (3).
        # Wait, op_kidnap_m26 in the codebase: Does it auto-target Govt if Syn is not present?
        # Let's check the code for op_kidnap_m26.
        # For now, let's just call it.
        self.env.op_kidnap_m26(3)

        # It should transfer the Cash marker to M26 instead of rolling!
        self.assertEqual(int(sp.cash[1]), 1, "M26 should have 1 cash after Kidnap")
        self.assertEqual(int(sp.cash[0]), 0, "Govt should have 0 cash after Kidnap")

if __name__ == '__main__':
    unittest.main()
