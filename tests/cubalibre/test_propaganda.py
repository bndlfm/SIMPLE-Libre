import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.constants import (
    US_ALLIANCE_EMBARGOED,
    US_ALLIANCE_FIRM,
    US_ALLIANCE_RELUCTANT,
)


class TestPropaganda2018Partial(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        # clean board state relevant to propaganda
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 1
            sp.sabotage = False
            sp.update_control()

        for p in self.env.players:
            p.resources = 0

        self.env.us_alliance = US_ALLIANCE_FIRM

    def test_government_earnings_econ_plus_aid_and_sabotage_excludes_ec(self):
        # Econ Centers: Cigar EC econ=3 (id=1), Textile EC econ=3 (id=6), Sugar Cane EC econ=2 (id=10)
        cigar = self.env.board.spaces[1]
        textile = self.env.board.spaces[6]
        sugar = self.env.board.spaces[10]
        self.assertEqual(cigar.type, 4)
        self.assertEqual(textile.type, 4)
        self.assertEqual(sugar.type, 4)

        # Sabotage cigar: M26+DR guerrillas outnumber cubes
        cigar.pieces[2] = 2  # M26 underground
        cigar.pieces[5] = 1  # DR underground
        cigar.pieces[0] = 0  # Troops
        cigar.pieces[1] = 0  # Police

        # Sugar not sabotaged: cubes >= insurgent
        sugar.pieces[0] = 1
        sugar.pieces[2] = 1

        self.env.aid = 5
        self.env.players[0].resources = 0

        self.env.resolve_propaganda()

        # Income includes all unsabotaged EC econ plus Aid.
        # Here: Textile (3) + Sugar (2) + Aid (5) = 10 (Cigar excluded due to sabotage)
        self.assertEqual(self.env.players[0].resources, 10)
        # Total Support <= 18 triggers alliance degrade and Aid -10 (min 0)
        self.assertEqual(self.env.us_alliance, US_ALLIANCE_RELUCTANT)
        self.assertEqual(self.env.aid, 0)

    def test_reset_clears_terror_and_flips_active_guerrillas_underground(self):
        sp = self.env.board.spaces[3]
        # Active guerrillas exist
        sp.pieces[3] = 2
        sp.pieces[6] = 1
        sp.pieces[9] = 3
        sp.terror = 2

        self.env.aid = 0
        self.env.resolve_propaganda()

        self.assertEqual(sp.terror, 0)
        self.assertEqual(sp.pieces[3], 0)
        self.assertEqual(sp.pieces[6], 0)
        self.assertEqual(sp.pieces[9], 0)
        self.assertEqual(sp.pieces[2], 2)
        self.assertEqual(sp.pieces[5], 1)
        self.assertEqual(sp.pieces[8], 3)

    def test_us_alliance_test_reduces_aid_even_when_embargoed(self):
        self.env.us_alliance = US_ALLIANCE_EMBARGOED
        self.env.aid = 3

        self.env.resolve_propaganda()

        self.assertEqual(self.env.us_alliance, US_ALLIANCE_EMBARGOED)
        self.assertEqual(self.env.aid, 0)


if __name__ == "__main__":
    unittest.main()
