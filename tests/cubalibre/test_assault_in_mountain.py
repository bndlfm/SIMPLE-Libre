import unittest
import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv

class Test_test_assault_in_mountain(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False)
        self.env.reset(seed=42)

    def test_assault_in_mountain(self):
        # Sierra Maestra (Space 4) is Mountain (type 3)
        sp = self.env.board.spaces[11]
        self.assertEqual(sp.type, 3, "Sierra Maestra should be a Mountain")

        sp.pieces[:] = 0
        sp.govt_bases = 0

        # 3 Troops, 2 Active M26 Guerrillas
        sp.pieces[0] = 3
        sp.pieces[3] = 2

        self.env.current_player_num = 0 # Govt

        # Assault should kill exactly 1 piece: floor(3 / 2) = 1
        # No skip_armored_cars_redeploy = False, context = "OP"
        self.env._op_assault_impl(11, target_faction=1)

        self.assertEqual(int(sp.pieces[3]), 1, "Assault in mountain should kill exactly 1 piece for 3 troops")


if __name__ == '__main__':
    unittest.main()
