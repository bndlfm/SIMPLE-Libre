import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestPropagandaVictoryChecks(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.sabotage = False
            sp.pieces[10] = 0
            sp.update_control()

        for p in self.env.players:
            p.resources = 0

    def test_govt_victory_uses_support_track(self):
        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 1
                sp.support_active = True
                sp.update_control()

        self.env.total_support_track = 0
        self.assertTrue(self.env.resolve_propaganda())
        self.assertGreater(self.env.total_support_track, 18)

    def test_govt_does_not_win_at_18_support(self):
        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 1
                sp.support_active = False
                sp.update_control()

        self.env._refresh_campaign_tracks()
        # Build an exact Total Support of 18 (boundary is strictly > 18 for Govt victory).
        # Passive Support contributes 1x population, Active Support contributes 2x population.
        # Flip a pop-1 space to Active Support to add exactly +1.
        if self.env.total_support_track != 18:
            bump = None
            for sp in self.env.board.spaces:
                if sp.type in [0, 1, 2, 3] and int(sp.population) == 1:
                    bump = sp
                    break
            self.assertIsNotNone(bump)
            bump.support_active = True
            bump.update_control()
            self.env._refresh_campaign_tracks()
        self.assertEqual(self.env.total_support_track, 18)
        self.assertEqual(self.env._propaganda_victory_check(), -1)

    def test_govt_requires_all_cities_active_support(self):
        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 1
                sp.support_active = True
                sp.update_control()

        havana = self.env.board.spaces[3]
        self.assertEqual(havana.type, 0)
        havana.support_active = False
        havana.update_control()

        self.env._refresh_campaign_tracks()
        self.assertGreater(self.env.total_support_track, 18)
        self.assertEqual(self.env._propaganda_victory_check(), -1)

    def test_m26_victory_uses_opposition_plus_bases_track(self):
        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 2
                sp.support_active = True
                sp.update_control()

        self.env.opposition_plus_bases_track = 0
        self.assertTrue(self.env.resolve_propaganda())
        self.assertGreater(self.env.opposition_plus_bases_track, 15)

    def test_dr_victory_uses_dr_pop_plus_bases_track(self):
        target = self.env.board.spaces[0]
        target.pieces[7] = 10  # DR Bases
        target.update_control()

        self.env.dr_pop_plus_bases_track = 0
        self.assertTrue(self.env.resolve_propaganda())
        self.assertGreater(self.env.dr_pop_plus_bases_track, 9)

    def test_syndicate_victory_uses_open_casinos_track(self):
        target = self.env.board.spaces[0]
        target.pieces[10] = 8  # Casinos
        target.update_control()

        self.env.players[3].resources = 31
        self.env.open_casinos_track = 0
        self.assertTrue(self.env.resolve_propaganda())
        self.assertGreater(self.env.open_casinos_track, 7)

    def test_syndicate_does_not_win_at_30_resources(self):
        target = self.env.board.spaces[0]
        target.pieces[10] = 8
        target.update_control()

        self.env.players[3].resources = 30
        self.assertEqual(self.env._propaganda_victory_check(), -1)

    def test_govt_wins_priority_over_m26_when_both_met(self):
        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 1
                sp.support_active = True
                sp.update_control()

        for sp in self.env.board.spaces:
            sp.pieces[4] = 0
        self.env.board.spaces[0].pieces[4] = 16
        self.env.board.spaces[0].update_control()

        self.assertEqual(self.env._propaganda_victory_check(), 0)

    def test_m26_wins_priority_over_dr_when_both_met(self):
        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 2
                sp.support_active = True
                sp.update_control()

        for sp in self.env.board.spaces:
            sp.pieces[4] = 0
            sp.pieces[7] = 0

        self.env.board.spaces[0].pieces[4] = 16
        self.env.board.spaces[1].pieces[7] = 10
        self.env.board.spaces[0].update_control()
        self.env.board.spaces[1].update_control()

        self.assertEqual(self.env._propaganda_victory_check(), 1)

    def test_dr_wins_priority_over_syndicate_when_both_met(self):
        target = self.env.board.spaces[0]
        target.pieces[7] = 10
        target.update_control()

        casino = self.env.board.spaces[1]
        casino.pieces[10] = 8
        casino.update_control()

        self.env.players[3].resources = 40

        self.assertEqual(self.env._propaganda_victory_check(), 2)

    def test_govt_wins_priority_over_dr_when_both_met(self):
        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 1
                sp.support_active = True
                sp.update_control()

        dr_space = self.env.board.spaces[0]
        dr_space.pieces[7] = 10
        dr_space.update_control()

        self.assertEqual(self.env._propaganda_victory_check(), 0)

    def test_govt_wins_priority_over_syndicate_when_both_met(self):
        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 1
                sp.support_active = True
                sp.update_control()

        casino = self.env.board.spaces[1]
        casino.pieces[10] = 8
        casino.update_control()

        self.env.players[3].resources = 40

        self.assertEqual(self.env._propaganda_victory_check(), 0)


if __name__ == "__main__":
    unittest.main()
