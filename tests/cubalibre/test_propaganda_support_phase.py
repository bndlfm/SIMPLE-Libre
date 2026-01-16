import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestPropagandaSupportPhase(unittest.TestCase):
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

    def test_civic_action_spends_resources_and_builds_support(self):
        sp = self.env.board.spaces[3]  # Havana (city)
        sp.pieces[0] = 1  # Troops
        sp.pieces[1] = 1  # Police
        sp.terror = 1
        sp.update_control()

        for ec in self.env.board.spaces:
            if ec.type == 4:
                ec.pieces[2] = 1

        self.env.aid = 0
        self.env.players[0].resources = 8

        self.env.resolve_propaganda()

        self.assertEqual(sp.terror, 0)
        self.assertEqual(sp.alignment, 1)
        self.assertFalse(sp.support_active)
        self.assertEqual(self.env.players[0].resources, 0)

    def test_agitation_spends_resources_and_removes_terror(self):
        sp = self.env.board.spaces[8]  # Camaguey City
        sp.pieces[2] = 2  # M26 guerrillas
        sp.terror = 1
        sp.update_control()

        self.env.players[1].resources = 1

        self.env.resolve_propaganda()

        self.assertEqual(sp.terror, 0)
        self.assertEqual(self.env.players[1].resources, 0)

    def test_expat_backing_free_rally(self):
        sp = self.env.board.spaces[12]  # Santiago De Cuba (city)
        for other in self.env.board.spaces:
            if other.id == sp.id:
                continue
            other.pieces[0] = 1
            other.update_control()
        self.env.players[2].available_forces[0] = 1

        self.env.resolve_propaganda()

        self.assertEqual(sp.pieces[5], 1)

    def test_final_propaganda_skips_resources_phase(self):
        self.env.propaganda_cards_played = 4
        self.env.aid = 5
        self.env.players[0].resources = 0

        self.env.resolve_propaganda()

        self.assertEqual(self.env.players[0].resources, 0)

    def test_reset_opens_closed_casinos(self):
        sp = self.env.board.spaces[5]
        sp.pieces[10] = 0
        sp.closed_casinos = 2
        sp.update_control()

        self.env.resolve_propaganda()

        self.assertEqual(sp.closed_casinos, 0)
        self.assertEqual(sp.pieces[10], 2)


if __name__ == "__main__":
    unittest.main()
