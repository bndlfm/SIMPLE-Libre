import unittest
import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv

class Test_test_attack_closes_unprotected_casinos(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False)
        self.env.reset(seed=42)

    def test_attack_closes_unprotected_casinos(self):
        # Setup Havana (Space 3)
        sp = self.env.board.spaces[3]
        sp.pieces[:] = 0
        sp.govt_bases = 0
        sp.closed_casinos = 0

        # Add M26 pieces for attacking
        sp.pieces[2] = 4 # UG
        sp.pieces[3] = 4 # Active

        # Add Syndicate Casino, but NO Police/Troops/Syn Guerrillas
        sp.pieces[10] = 1 # Open Casino

        self.env.current_player_num = 1 # M26

        # Trigger attack insurgent
        # Removals=1. Since Casino is unprotected, it should be the only target.
        # It should automatically close the Casino.
        self.env._op_attack_insurgent(3, 2, 3, 4, skip_roll=True, removals_left=1)

        self.assertEqual(int(sp.pieces[10]), 0, "Casino should be closed")
        self.assertEqual(int(sp.closed_casinos), 1, "Closed Casinos should increase")


if __name__ == '__main__':
    unittest.main()
