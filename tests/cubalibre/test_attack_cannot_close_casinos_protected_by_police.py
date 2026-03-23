import unittest
import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv

class Test_test_attack_cannot_close_casinos_protected_by_police(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False)
        self.env.reset(seed=42)

    def test_attack_cannot_close_casinos_protected_by_police(self):
        # Setup Havana (Space 3)
        sp = self.env.board.spaces[3]
        sp.pieces[:] = 0
        sp.govt_bases = 0

        # Add M26 pieces for attacking
        sp.pieces[2] = 4 # UG
        sp.pieces[3] = 4 # Active

        # Add Syndicate Casino and Police
        sp.pieces[10] = 1 # Open Casino
        sp.pieces[1] = 1  # Police

        self.env.current_player_num = 1 # M26

        # Trigger attack insurgent
        # Removals=1. Since Casino is protected, Govt (Police) is the only target.
        # It should automatically kill the Police and leave the Casino open.
        self.env._op_attack_insurgent(3, 2, 3, 4, skip_roll=True, removals_left=1)

        self.assertEqual(int(sp.pieces[1]), 0, "Police should be killed")
        self.assertEqual(int(sp.pieces[10]), 1, "Casino should survive (protected by Police)")


if __name__ == '__main__':
    unittest.main()
