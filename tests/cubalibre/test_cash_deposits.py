import random
import unittest

import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestCashDeposits(unittest.TestCase):
    def setUp(self):
        self._random_state = random.getstate()
        self._np_random_state = np.random.get_state()
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        # Clean board
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.sabotage = False
            sp.closed_casinos = 0
            sp.cash[:] = 0
            sp.cash_holders[:] = 0
            sp.update_control()

        for p in self.env.players:
            p.resources = 0

        self.env.aid = 0

    def tearDown(self):
        random.setstate(self._random_state)
        np.random.set_state(self._np_random_state)

    def test_cash_deposits_remove_cash_and_convert_to_bases_or_resources(self):
        sp = self.env.board.spaces[3]

        # Give each faction 1 cash in Havana (attach to a piece).
        sp.pieces[0] = 1  # Govt Troop
        sp.pieces[2] = 1  # M26 Underground
        sp.pieces[5] = 1  # DR Underground
        sp.pieces[8] = 1  # Syndicate Underground
        self.env._add_cash_marker(sp, 0)
        self.env._add_cash_marker(sp, 1)
        self.env._add_cash_marker(sp, 2)
        self.env._add_cash_marker(sp, 3)

        # Ensure bases are available so deposits become bases/casino.
        self.env.players[0].available_bases = 1
        self.env.players[1].available_bases = 1
        self.env.players[2].available_bases = 1
        self.env.players[3].available_bases = 1

        # Not final propaganda
        self.env.propaganda_cards_played = 1
        self.env.resolve_propaganda()

        self.assertEqual(int(sp.cash[0] + sp.cash[1] + sp.cash[2] + sp.cash[3]), 0)
        self.assertEqual(int(sp.govt_bases), 1)
        self.assertEqual(int(sp.pieces[4]), 1)
        self.assertEqual(int(sp.pieces[7]), 1)
        self.assertEqual(int(sp.pieces[10]), 1)

    @unittest.skip("Covered by tests/cubalibre/test_card_22_raul.py")
    def test_raul_shaded_kidnap_adds_aid_twice_resources_taken(self):
        self.env.players[0].resources = 2
        self.env.aid = 0
        self.env.capabilities.add("Raul_Shaded")

        self.env.op_kidnap_m26(3)

        self.assertEqual(self.env.aid, 4)


if __name__ == "__main__":
    unittest.main()
