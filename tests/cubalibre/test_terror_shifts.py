import unittest
import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv

class Test_test_terror_shifts(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False)
        self.env.reset(seed=42)

    def test_terror_shifts(self):
        # M26 Terror shifts toward Active Opposition
        # Others (e.g. DR) shift toward Neutral

        # Setup Havana (Space 3, City) for M26
        havana_m26 = self.env.board.spaces[3]
        havana_m26.alignment = 1 # Passive Support
        havana_m26.support_active = False
        havana_m26.pieces[:] = 0
        havana_m26.pieces[2] = 1 # M26 UG

        self.env.current_player_num = 1 # M26
        self.env._op_terror_insurgent(3, 2, 3) # M26: u=2, a=3

        # Passive Support -> Neutral (alignment 0)
        self.assertEqual(havana_m26.alignment, 0, "M26 Terror from Passive Support should shift to Neutral")

        # Setup another space for M26: from Neutral to Passive Opposition
        las_villas_m26 = self.env.board.spaces[5]
        las_villas_m26.alignment = 0 # Neutral
        las_villas_m26.pieces[:] = 0
        las_villas_m26.pieces[2] = 1 # M26 UG

        self.env._op_terror_insurgent(5, 2, 3)
        self.assertEqual(las_villas_m26.alignment, 2, "M26 Terror from Neutral should shift to Passive Opposition")
        self.assertFalse(las_villas_m26.support_active, "Should be Passive")

        # Now test DR Terror
        # Setup Camaguey (Space 6) from Passive Opposition
        camaguey_dr = self.env.board.spaces[7]
        camaguey_dr.alignment = 2 # Passive Opposition
        camaguey_dr.support_active = False
        camaguey_dr.pieces[:] = 0
        camaguey_dr.pieces[5] = 1 # DR UG

        self.env.current_player_num = 2 # DR
        self.env._op_terror_insurgent(7, 5, 6) # DR: u=5, a=6

        # Passive Opposition -> Neutral (alignment 0)
        self.assertEqual(camaguey_dr.alignment, 0, "DR Terror from Passive Opposition should shift to Neutral")


if __name__ == '__main__':
    unittest.main()
