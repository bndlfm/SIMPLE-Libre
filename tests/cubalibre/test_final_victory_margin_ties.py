import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestFinalVictoryMarginTies(unittest.TestCase):
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

    def test_final_victory_ranking_prefers_syndicate_on_tie(self):
        # Tie margins at 0 should go to Syndicate per 7.1.
        self.env.victory_margins = lambda: [0, 0, 0, 0]
        ranking = self.env.final_victory_ranking()
        self.assertEqual(ranking[0], 3)

    def test_final_victory_ranking_tie_order(self):
        # All margins equal; tie order should be Syndicate > DR > M26 > Govt.
        self.env.victory_margins = lambda: [0, 0, 0, 0]
        ranking = self.env.final_victory_ranking()
        self.assertEqual(ranking, [3, 2, 1, 0])

    def test_final_victory_ranking_breaks_partial_tie(self):
        # Syndicate and DR tie for top margin; Syndicate should win the tie.
        self.env.victory_margins = lambda: [1, 2, 2, 2]
        ranking = self.env.final_victory_ranking()
        self.assertEqual(ranking[0], 3)


if __name__ == "__main__":
    unittest.main()
