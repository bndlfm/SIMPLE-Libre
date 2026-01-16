import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestPropagandaInsurgentEarningsAndSkim(unittest.TestCase):
    def setUp(self):
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
            sp.update_control()

        for p in self.env.players:
            p.resources = 0

        self.env.aid = 0

    def test_insurgent_earnings_m26_bases_dr_spaces_syn_formula(self):
        # M26: 2 bases on map => +2 (use ECs to avoid Agitation spending)
        self.env.board.spaces[1].pieces[4] = 1
        self.env.board.spaces[6].pieces[4] = 1
        self.env.board.spaces[1].update_control()
        self.env.board.spaces[6].update_control()

        # DR: pieces in 2 spaces => +2
        self.env.board.spaces[5].pieces[5] = 1
        self.env.board.spaces[9].pieces[6] = 2

        # Syndicate:
        # - Havana city pop 6, Syn guerrillas (8+9) outnumber police
        havana = self.env.board.spaces[3]
        havana.pieces[8] = 2
        havana.pieces[1] = 1

        # - Sugar Cane EC econ 2 unsabotaged, Syn outnumber police
        sugar = self.env.board.spaces[10]
        sugar.pieces[8] = 1
        sugar.pieces[1] = 0
        sugar.sabotage = False

        # - 2 open casinos anywhere => +4
        self.env.board.spaces[3].pieces[10] = 2

        self.env.resolve_propaganda()

        self.assertEqual(self.env.players[1].resources, 2)
        self.assertEqual(self.env.players[2].resources, 2)
        # Syndicate: 6 (Havana pop) + 2 (Sugar econ) + 4 (2*casinos) = 12
        self.assertEqual(self.env.players[3].resources, 12)

    def test_skim_transfers_to_controlling_faction_and_respects_santo_block(self):
        # Prevent Government earnings (6.2.1) from affecting assertions.
        for sp in self.env.board.spaces:
            if sp.type == 4:
                sp.sabotage = True

        # Make a casino space controlled by Govt and another by M26.
        # Control logic counts all pieces, including casinos.
        sp_govt = self.env.board.spaces[3]
        sp_govt.pieces[10] = 1  # open casino
        sp_govt.pieces[0] = 3   # troops
        sp_govt.update_control()
        self.assertEqual(sp_govt.controlled_by, 1)

        sp_m26 = self.env.board.spaces[12]
        sp_m26.pieces[10] = 1
        sp_m26.pieces[2] = 3
        sp_m26.alignment = 2
        sp_m26.support_active = True
        sp_m26.update_control()
        self.assertEqual(sp_m26.controlled_by, 2)

        self.env.players[3].resources = 10

        self.env.resolve_propaganda()

        # 6.2.2 adds +2 per open casino, then 6.2.3 transfers 2 per casino space.
        # Here: 2 open casinos => +4, then two casino spaces skim 2 each => -4.
        self.assertEqual(self.env.players[3].resources, 10)
        self.assertEqual(self.env.players[0].resources, 2)
        self.assertEqual(self.env.players[1].resources, 2)

        # Now enable Santo (Trafficante_Shaded): Underground Syn blocks skim in that space.
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.sabotage = False
            sp.update_control()

        for sp in self.env.board.spaces:
            if sp.type == 4:
                sp.sabotage = True
        for p in self.env.players:
            p.resources = 0

        sp_blocked = self.env.board.spaces[3]
        sp_blocked.pieces[10] = 1
        sp_blocked.pieces[8] = 1  # underground syn
        sp_blocked.pieces[0] = 3  # govt troops => govt controls
        sp_blocked.update_control()
        self.assertEqual(sp_blocked.controlled_by, 1)

        self.env.players[3].resources = 10
        self.env.capabilities.add("Trafficante_Shaded")

        self.env.resolve_propaganda()

        # Blocked: no transfer, but Syndicate still earns +2 per open casino.
        # Also earns City population (Havana pop=6) because Syn guerrillas outnumber Police.
        self.assertEqual(self.env.players[3].resources, 18)
        self.assertEqual(self.env.players[0].resources, 0)


if __name__ == "__main__":
    unittest.main()
