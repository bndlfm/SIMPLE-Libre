import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestScoringAndControl(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=1)

        # clear to a known state
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.update_control()

    def test_control_and_scoring_basic(self):
        # Havana (3): govt controls if cubes > insurgents
        self.env.board.add_piece(3, 0, 0)  # troop
        self.env.board.add_piece(3, 0, 1)  # police
        self.env.board.add_piece(3, 0, 0)
        self.env.board.add_piece(3, 0, 1)
        # 2 M26 underground
        self.env.board.add_piece(3, 1, 0)
        self.env.board.add_piece(3, 1, 0)
        self.env.board.spaces[3].alignment = 1
        self.env.board.spaces[3].update_control()

        self.assertEqual(self.env.board.spaces[3].controlled_by, 1)

        # Las Villas (5): DR control by presence
        self.env.board.add_piece(5, 2, 0)
        self.env.board.add_piece(5, 2, 0)
        self.env.board.add_piece(5, 2, 0)
        self.env.board.spaces[5].update_control()
        self.assertEqual(self.env.board.spaces[5].controlled_by, 3)

        # Santiago (12): M26 opposition base contributes to score
        self.env.board.spaces[12].alignment = 2
        self.env.board.add_piece(12, 1, 2)

        scores = self.env.score_game()

        # Govt: Havana pop (6) counted twice when support+control in this simplified scoring
        self.assertEqual(scores[0], 12)
        # M26: opposition pop 1 + bases 1
        self.assertEqual(scores[1], 2)


if __name__ == "__main__":
    unittest.main()
