import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestVictoryMarkers(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        # Start from a clean, deterministic board
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.update_control()

    def test_total_support_formula(self):
        # Make Havana (pop 6) Active Support => contributes 12
        havana = self.env.board.spaces[3]
        self.assertEqual(havana.population, 6)
        havana.alignment = 1
        havana.support_active = True

        # Make Santiago (pop 1) Passive Support => contributes 1
        santiago = self.env.board.spaces[12]
        self.assertEqual(santiago.population, 1)
        santiago.alignment = 1
        santiago.support_active = False

        self.assertEqual(self.env.total_support_value(), 13)

    def test_opposition_plus_bases(self):
        # Santiago (pop 1) Active Opposition => contributes 2
        santiago = self.env.board.spaces[12]
        santiago.alignment = 2
        santiago.support_active = True

        # Add 1 M26 base anywhere
        self.env.board.spaces[12].pieces[4] = 1

        self.assertEqual(self.env.opposition_plus_bases_value(), 3)

    def test_dr_pop_plus_bases(self):
        # Pick Las Villas (pop 2), ensure DR controls it
        lv = self.env.board.spaces[5]
        self.assertEqual(lv.population, 2)
        lv.pieces[5] = 3  # DR underground
        lv.update_control()
        self.assertEqual(lv.controlled_by, 3)

        # Add 1 DR base
        lv.pieces[7] = 1
        lv.update_control()

        self.assertEqual(self.env.dr_pop_plus_bases_value(), 3)

    def test_open_casinos(self):
        # Add casinos in two spaces
        self.env.board.spaces[3].pieces[10] = 2
        self.env.board.spaces[0].pieces[10] = 1
        self.assertEqual(self.env.open_casinos_value(), 3)


if __name__ == "__main__":
    unittest.main()
