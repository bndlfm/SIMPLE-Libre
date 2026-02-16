import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestCasinoStackingRules(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.closed_casinos = 0
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            sp.update_control()

    def test_can_place_casino_disallows_econ_space_type_4(self):
        sp = self.env.board.spaces[0]
        sp.type = 4
        self.assertFalse(self.env._can_place_casino(sp))

    def test_can_place_casino_disallows_third_casino(self):
        sp = self.env.board.spaces[0]
        sp.type = 0
        sp.pieces[10] = 2
        self.assertFalse(self.env._can_place_casino(sp))

    def test_can_place_casino_disallows_when_more_than_two_non_casino_bases(self):
        sp = self.env.board.spaces[0]
        sp.type = 0
        sp.govt_bases = 3
        self.assertFalse(self.env._can_place_casino(sp))

        sp.govt_bases = 2
        sp.pieces[4] = 1  # M26 base
        self.assertFalse(self.env._can_place_casino(sp))

    def test_can_place_casino_allows_when_two_or_fewer_non_casino_bases_and_less_than_two_casinos(self):
        sp = self.env.board.spaces[0]
        sp.type = 0
        sp.govt_bases = 1
        sp.pieces[4] = 1  # M26 base
        sp.pieces[10] = 1
        self.assertTrue(self.env._can_place_casino(sp))


if __name__ == "__main__":
    unittest.main()
