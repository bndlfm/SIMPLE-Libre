import unittest
from app.environments.cubalibre.envs.env import CubaLibreEnv

class TestCasinoStackingEdgeCases(unittest.TestCase):
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

    def test_can_place_casino_fails_if_2_casinos_exist(self):
        # 8.4.2 Stacking: A space may hold maximum 2 Casinos
        sp = self.env.board.spaces[3] # Havana
        sp.type = 0 # City
        sp.pieces[10] = 2 # 2 Syndicate Casinos

        self.assertFalse(self.env._can_place_casino(sp), "Cannot place a 3rd casino in a space")

    def test_can_place_casino_fails_if_space_has_max_non_casino_bases(self):
        # 8.4.2 Stacking: A space may hold maximum 2 Casinos AND maximum 2 non-Casino Bases (Govt, M26, DR).
        # Wait, the rule actually says: "maximum 2 non-Casino Bases... AND maximum 2 Casinos".
        # This implies the two limits are separate! 2 non-Casino bases AND 2 Casinos can coexist.
        # But wait, looking at `_can_place_casino`, the engine currently says:
        # non_casino_bases = int(sp.govt_bases + sp.pieces[4] + sp.pieces[7])
        # if non_casino_bases > 2: return False
        # Let's ensure a space CAN hold 2 non-casino bases AND 1 casino, and then CAN hold a 2nd casino.

        sp = self.env.board.spaces[3]
        sp.type = 0
        sp.govt_bases = 1
        sp.pieces[4] = 1 # M26 base
        # Space now has 2 non-casino bases.

        sp.pieces[10] = 1 # 1 Casino

        # It should STILL allow another casino, because the limits are independent (2 of each).
        self.assertTrue(self.env._can_place_casino(sp), "Space should allow 2 Casinos even if it has 2 non-Casino bases")

        # However, if somehow there are 3 non-casino bases (which is illegal, but let's test the env logic),
        # the env currently rejects casino placement. Let's see if we should test that.
        sp.govt_bases = 2
        sp.pieces[4] = 1 # 3 non-casino bases
        self.assertFalse(self.env._can_place_casino(sp), "Env shouldn't allow casino if non-casino bases > 2 (though that state shouldn't happen)")

    def test_can_place_casino_fails_in_economic_centers(self):
        # Economic Centers (type 4) cannot hold Bases or Casinos (only 1 or 2 pieces total, no bases allowed by map definition).
        sp = self.env.board.spaces[10] # e.g. some Econ Center if 10 is one
        sp.type = 4
        self.assertFalse(self.env._can_place_casino(sp), "Cannot place casinos in Economic Centers")

    def test_can_place_casino_allows_in_provinces_cities_and_mountains(self):
        for t in [0, 1, 2, 3]: # City, Province, Mountain, etc.
            sp = self.env.board.spaces[0]
            sp.type = t
            sp.pieces[10] = 0
            sp.govt_bases = 0
            sp.pieces[4] = 0
            sp.pieces[7] = 0
            self.assertTrue(self.env._can_place_casino(sp), f"Should allow casino in space type {t}")

if __name__ == '__main__':
    unittest.main()
