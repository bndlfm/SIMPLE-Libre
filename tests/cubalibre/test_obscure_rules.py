import unittest
import unittest.mock
import numpy as np
from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.constants import *

class TestObscureRules(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv()
        self.env.reset()
        self.env.capabilities.clear()
        self.clear_board()
        # Set a neutral card for all tests unless specified otherwise
        from app.environments.cubalibre.envs.classes import Card
        self.env.current_card = Card(99, 'Neutral', [0, 1, 2, 3], '', '')
        self.env.card_action_slot = 0
        for p in self.env.players:
            p.eligible = True

    def clear_board(self):
        for sp in self.env.board.spaces:
            sp.pieces.fill(0)
            sp.govt_bases = 0
            sp.closed_casinos = 0
            sp.terror = 0
            sp.sabotage = False
            sp.alignment = 0
            sp.support_active = False
            sp.cash_holders.fill(0)
            sp.cash_owner_by_holder.fill(-1)
            sp.refresh_cash_counts()
            sp.update_control()
        self.env.set_aid(0)
        self.env.set_us_alliance(US_ALLIANCE_FIRM)
        self.env._refresh_campaign_tracks()

    def test_assault_underground_protection(self):
        """
        Rule 3.2.4: Assault removes Active pieces first, then Bases.
        Note 3.2.4: "An Operation cannot remove an enemy Base as long as Guerrillas (Active or Underground)... remain".
        """
        # Setup: Oriente with 1 M26 Base, 1 M26 Underground Guerrilla, and 3 Govt Troops.
        space = self.env.board.spaces[9] # Oriente
        space.pieces.fill(0)
        space.govt_bases = 0
        space.pieces[2] = 1 # M26 UG
        space.pieces[4] = 1 # M26 Base
        space.pieces[0] = 3 # Govt Troops
        space.update_control()

        self.env.current_player_num = 0 # Govt
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        # Action: Assault in Oriente
        action = self.env._ops_action_base + OP_ASSAULT * 13 + 9
        self.env.step(action)

        # Base should be protected by UG
        self.assertEqual(space.pieces[4], 1, "Base should be protected by Underground Guerrilla")
        self.assertEqual(space.pieces[2], 1, "Underground Guerrilla should be safe from Troops without Police")

    def test_ambush_requirements(self):
        """
        Rule 4.3.2: Ambush Activates exactly 1 Underground Guerrilla,
        automatically succeeds (2 removals), and places 1 new Underground Guerrilla.
        """
        # Setup: Las Villas (5) with 1 M26 UG, 2 Govt Troops.
        space = self.env.board.spaces[5]
        space.pieces[2] = 1 # M26 UG
        space.pieces[0] = 2 # Govt Troops
        space.update_control()

        self.env.players[1].available_forces[0] = 5
        self.env.players[1].resources = 10
        self.env.current_player_num = 1 # M26

        # 1. Choose Ops
        self.env.step(self.env._main_action_base + MAIN_OPS)

        # 2. Choose Attack in Las Villas
        # Mock roll to fail so it doesn't auto-remove pieces before Ambush
        with unittest.mock.patch.object(self.env, '_roll_die', return_value=6):
            self.env.step(self.env._ops_action_base + OP_ATTACK_M26 * 13 + 5)

        # 3. Choose Special Activity: Ambush in Las Villas
        self.env.step(self.env._ops_action_base + OP_AMBUSH_M26 * 13 + 5)

        # Verification:
        self.assertEqual(space.pieces[3], 1, "One guerrilla should be Activated")
        self.assertEqual(space.pieces[2], 1, "One NEW guerrilla should be placed Underground")
        self.assertEqual(space.pieces[0], 0, "Two Govt pieces should be removed")
        self.assertEqual(self.env.players[1].available_forces[0], 4, "Available forces should decrease by 1")

    def test_attack_activates_all(self):
        """
        Rule 3.3.3: Attack "Activate all the executing Faction’s Guerrillas".
        """
        self.env.players[1].resources = 10

        # Setup: Las Villas with 3 M26 UG, 1 Govt Troop.
        space = self.env.board.spaces[5]
        space.pieces[2] = 3 # M26 UG
        space.pieces[0] = 1 # Govt Troop
        space.update_control()

        self.env.current_player_num = 1 # M26
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        # Mock roll to be failed (e.g. 6) so we don't get Captured Goods adding UG back
        # Important: Patch the instance or use the correct module path
        with unittest.mock.patch.object(self.env, '_roll_die', return_value=6):
            # Choose Attack in Las Villas
            action = self.env._ops_action_base + OP_ATTACK_M26 * 13 + 5
            self.env.step(action)

        # Verification: All 3 should be Active.
        self.assertEqual(space.pieces[2], 0, "All guerrillas should be activated regardless of roll")
        self.assertEqual(space.pieces[3], 3)

    def test_victory_tie_breaks(self):
        """
        Rule 7.1: Tie-break order: Non-player > Syndicate > Directorio > 26July.
        """
        self.env.propaganda_cards_played = 4
        self.env.total_support_track = 18
        self.env.opposition_plus_bases_track = 15
        self.env.dr_pop_plus_bases_track = 9
        self.env.open_casinos_track = 7
        self.env.players[3].resources = 30

        ranking = self.env.final_victory_ranking()

        self.assertEqual(ranking[0], 3, "Syndicate should win tie-break (margin 0 vs others margin 0)")
        self.assertEqual(ranking[1], 2, "DR should be 2nd in tie-break")
        self.assertEqual(ranking[2], 1, "M26 should be 3rd in tie-break")
        self.assertEqual(ranking[3], 0, "Govt should be last in tie-break")

    def test_cross_faction_launder(self):
        """
        Rule 2.3.6: A different Faction may remove its own Cash marker to enable
        the 1st or 2nd Eligible Faction to execute a free Limited Operation.
        """
        # Setup: M26 acting, Syndicate has cash.
        # Havana: Syndicate has piece index 8 (UG) and 1 cash.
        space = self.env.board.spaces[3] # Havana
        space.pieces.fill(0)
        space.pieces[8] = 1 # Syn UG
        space.cash_holders[8] = 1 # Syn UG holds cash
        space.update_control()

        self.env.players[1].resources = 10
        self.env.current_player_num = 1 # M26 acting
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        # 1. M26 performs a paid Op (Rally in Sierra Maestra)
        self.env.step(self.env._ops_action_base + OP_RALLY_M26 * 13 + 11)

        # 2. Skip SA to trigger Launder check.
        self.env.step(self.env._main_action_base + MAIN_PASS)

        # 3. Syndicate (3) provides cash.
        self.env.step(self.env._target_faction_action_base + 3)

        # 4. Select space for cash removal (Havana=3).
        self.env.step(self.env._target_space_action_base + 3)

        # 5. Verification: Cash was removed.
        self.assertEqual(space.cash_holders[8], 0)
        self.assertTrue(self.env._launder_free)

    def test_us_alliance_aid_degradation(self):
        """
        Rule 6.3.1: reduce Aid by –10 even if already at Embargoed.
        """
        self.env.total_support_track = 10 # Force degradation
        self.env.set_aid(5)
        self.env.set_us_alliance(US_ALLIANCE_EMBARGOED)

        self.env._propaganda_us_alliance_test()

        self.assertEqual(self.env.aid, 0, "Aid should be 0 (5 - 10, clamped)")
        self.assertEqual(self.env.us_alliance, US_ALLIANCE_EMBARGOED, "Should stay at Embargoed")

    def test_attack_captured_goods(self):
        """
        Rule 3.3.3: roll of '1' places 1 Available Guerrilla.
        """
        space = self.env.board.spaces[5]
        space.pieces.fill(0)
        space.pieces[3] = 3 # M26 Active
        space.pieces[0] = 1 # Govt Troop
        space.update_control()

        self.env.players[1].available_forces[0] = 5
        self.env.current_player_num = 1 # M26
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        # Mock die roll to 1
        with unittest.mock.patch.object(CubaLibreEnv, '_roll_die', return_value=1):
            self.env.step(self.env._ops_action_base + OP_ATTACK_M26 * 13 + 5)

        # Verification: Successfully attacked (removed Troop) AND placed new guerrilla (UG).
        self.assertEqual(space.pieces[0], 0, "Govt Troop should be removed")
        self.assertEqual(space.pieces[2], 1, "New M26 UG should be placed on roll of 1")
        self.assertEqual(self.env.players[1].available_forces[0], 4)

    def test_final_event_card_limop_restriction(self):
        """
        Rule 2.3.9: last Event card before final Propaganda restricted to Limited Ops.
        """
        from app.environments.cubalibre.envs.classes import PropagandaCard, Card
        # Set next card to 4th Propaganda
        self.env.next_card = PropagandaCard(103)
        self.env.propaganda_cards_played = 3

        # Action slot 0 (1st eligible)
        self.env.card_action_slot = 0
        self.env.phase = PHASE_CHOOSE_MAIN

        mask = self.env.legal_actions

        # OPS should be masked out, Limited OPS should be allowed.
        self.assertEqual(mask[self.env._main_action_base + MAIN_OPS], 0, "Full Ops should be illegal on final event card")
        self.assertEqual(mask[self.env._limited_main_action_id], 1, "Limited Ops should be legal on final event card")

    def test_mandatory_troop_redeploy_priority(self):
        """
        Rule 6.4.2: mandatory troop movement to City/Base or Havana if none.
        """
        # Setup: Troops on Cigar EC (1), no Govt Bases or Cities under Govt control.
        self.env.board.spaces[1].pieces[0] = 5 # Troops on EC
        # Clear default Govt control of cities
        for s_id in [3, 8, 12]:
            self.env.board.spaces[s_id].pieces.fill(0)
            self.env.board.spaces[s_id].pieces[2] = 10 # M26 control
            self.env.board.spaces[s_id].update_control()

        self.env.board.spaces[3].govt_bases = 0 # No base in Havana
        self.env.board.spaces[3].update_control()

        # Call deterministic redeploy
        self.env._redeploy_government_deterministic()

        # Verification: Mandatory redeploy should have moved them to Havana City (3)
        self.assertEqual(self.env.board.spaces[1].pieces[0], 0, "Troops must leave EC")
        self.assertEqual(self.env.board.spaces[3].pieces[0], 5, "Troops must go to Havana City if no Govt cities/bases")

    def test_rally_flip_choice(self):
        """
        Rule 3.3.1: Rally "place... available... or flip all... underground".
        If a base is present, choice is possible.
        """
        # Setup: M26 has Base in Sierra Maestra, 3 Active Guerrillas, 10 Available.
        space = self.env.board.spaces[11]
        space.pieces.fill(0)
        space.pieces[4] = 1 # M26 Base
        space.pieces[3] = 3 # M26 Active
        space.update_control()

        self.env.players[1].available_forces[0] = 10
        self.env.players[1].resources = 10
        self.env.current_player_num = 1 # M26
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        # M26 Rally
        action = self.env._ops_action_base + OP_RALLY_M26 * 13 + 11
        self.env.step(action)

        # Should be in PHASE_CHOOSE_EVENT_OPTION for Rally choice
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        # Choose Place (0)
        self.env.step(self.env._event_option_action_base + 0)

        # Sierra Maestra pop=1, Base=1. M26 Rally Cap = 2 * (1+1) = 4.
        # It should place 4 pieces. Total 3 Active, 4 UG.
        self.assertEqual(space.pieces[2], 4)
        self.assertEqual(space.pieces[3], 3)

    def test_sinatra_stacking_exception(self):
        """
        Rule 5.1.1/1.4.2: Events specification (Sinatra) may violate stacking.
        """
        # Rule 1.4.2: Max 2 non-Casino Bases.
        # Setup: Havana with 1 Govt Base, 1 M26 Base.
        space = self.env.board.spaces[3]
        space.pieces.fill(0)
        space.govt_bases = 1
        space.pieces[4] = 1 # M26 Base
        space.update_control()

        self.env.players[3].available_bases = 6
        self.env.current_player_num = 3 # Syndicate
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        # Action: Shaded Sinatra (Event 46)
        from app.environments.cubalibre.envs.classes import Card
        self.env.current_card = Card(46, 'Sinatra', [0, 1, 2, 3], '', '')

        self.env.step(self.env._event_side_base + EVENT_SHADED)

        # Havana should now have 1 Casino + 2 Bases = 3 total discs.
        self.assertEqual(space.pieces[10], 1, "Sinatra should place Casino regardless of stacking")
        self.assertEqual(space.govt_bases + space.pieces[4], 2, "Other bases should remain")

    def test_rally_restrictions(self):
        """
        Rule 3.3.1: 26July only at Neutral/Opposition, DR only at Neutral/Passive.
        """
        # Havana: Active Support
        space = self.env.board.spaces[3]
        space.alignment = 1
        space.support_active = True

        # 1. M26 should not be able to Rally in Havana
        self.env.current_player_num = 1 # M26
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        mask = self.env.legal_actions
        action_idx = self.env._ops_action_base + OP_RALLY_M26 * 13 + 3
        self.assertEqual(mask[action_idx], 0, "M26 should not be able to Rally in Active Support")

        # 2. DR should not be able to Rally in Havana
        self.env.current_player_num = 2 # DR
        mask = self.env.legal_actions
        action_idx = self.env._ops_action_base + OP_RALLY_DR * 13 + 3
        self.assertEqual(mask[action_idx], 0, "DR should not be able to Rally in Active Support")

        # 3. M26 should be able to Rally in Passive Opposition
        space.alignment = 2
        space.support_active = False
        self.env.current_player_num = 1 # M26
        mask = self.env.legal_actions
        action_idx = self.env._ops_action_base + OP_RALLY_M26 * 13 + 3
        self.assertEqual(mask[action_idx], 1, "M26 should be able to Rally in Passive Opposition")

        # 4. DR should be able to Rally in Passive Opposition
        self.env.current_player_num = 2 # DR
        mask = self.env.legal_actions
        action_idx = self.env._ops_action_base + OP_RALLY_DR * 13 + 3
        self.assertEqual(mask[action_idx], 1, "DR should be able to Rally in Passive Opposition")

        # 5. DR should NOT be able to Rally in Active Opposition
        space.support_active = True
        mask = self.env.legal_actions
        action_idx = self.env._ops_action_base + OP_RALLY_DR * 13 + 3
        self.assertEqual(mask[action_idx], 0, "DR should not be able to Rally in Active Opposition")

    def test_skim_logic(self):
        """
        Rule 6.2.3: Syndicate transfers 2 resources to Controlling faction per open Casino.
        Rule 5.3: Santo Capability - Underground Syn Guerrilla prevents Skim.
        """
        # Setup: Havana (3) with 1 open Casino. M26 Controls (index 1).
        space = self.env.board.spaces[3]
        space.pieces[10] = 1 # Open Casino
        space.pieces[2] = 5  # M26 guerrillas for control
        space.update_control()
        self.assertEqual(space.controlled_by, 2)

        self.env.players[1].resources = 10
        self.env.players[3].resources = 10
        self.env._refresh_campaign_tracks()

        # 1. Normal Skim
        self.env._propaganda_resources_phase()
        # Havana pop=6.
        # Syn earnings: Havana Syn G (0) <= Police (0). No pop income.
        # Open casinos: 2 * 1 = 2.
        # Skim: Syndicate (3) transfers 2 to M26 (1).
        # Total Syn = 10 - 2 (skim) + 2 (earnings) = 10.
        # M26 earnings = 0. Total M26 = 10 + 2 (skim) = 12.
        self.assertEqual(self.env.players[1].resources, 12)
        self.assertEqual(self.env.players[3].resources, 10)

        # 2. Santo Capability prevents Skim
        self.env.players[1].resources = 10
        self.env.players[3].resources = 10
        space.pieces[8] = 1 # Syndicate Underground Guerrilla
        self.env.capabilities.add("Trafficante_Shaded")
        self.env._refresh_campaign_tracks()
        self.env._propaganda_resources_phase()

        # M26 should NOT gain 2.
        # Syn earnings:
        # - Havana: Syn G (1) > Police (0). Earnings = Havana Pop = 6.
        # - Open Casinos: 2 * 1 = 2.
        # Total Syn income = 6 + 2 = 8.
        # Total Syn resources = 10 + 8 = 18.
        self.assertEqual(self.env.players[1].resources, 10, "M26 should not receive skim due to Santo")
        self.assertEqual(self.env.players[3].resources, 18)

    def test_pact_of_caracas_blocking(self):
        """
        Rule 5.3 (Event 18): Pact of Caracas prevents removal of each other's pieces or affecting Opposition.
        """
        # Setup: Las Villas with M26 UG and DR UG.
        space = self.env.board.spaces[5]
        space.pieces.fill(0)
        space.pieces[2] = 1 # M26 UG
        space.pieces[5] = 1 # DR UG
        space.update_control()

        self.env.capabilities.add("PactOfCaracas_Unshaded")
        self.env.same_player_control = False

        # 1. M26 Terror (Affecting Opposition)
        self.env.current_player_num = 1 # M26
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        mask = self.env.legal_actions
        # Terror M26 in Las Villas
        action_idx = self.env._ops_action_base + OP_TERROR_M26 * 13 + 5
        self.assertEqual(mask[action_idx], 0, "M26 Terror should be blocked by Pact of Caracas (assuming same_player=False)")

        # 2. DR Assassinate M26 piece
        self.env.current_player_num = 2 # DR
        # Assassinate DR in Las Villas
        action_idx = self.env._ops_action_base + OP_ASSASSINATE_DR * 13 + 5
        self.assertEqual(mask[action_idx], 0, "DR Assassinate should be blocked by Pact of Caracas")

    def test_march_limited_vs_full(self):
        """
        Rule 3.3.2: Limited March restricted to single destination.
        Full March allows multiple destinations.
        """
        # This is more of a Legal Actions test.
        self.env.current_player_num = 1 # M26
        self.env.players[1].eligible = True
        self.env.players[1].resources = 10

        # Sierra Maestra (11) has M26.
        self.env.board.spaces[11].pieces[2] = 1

        # 1. Full Ops: March can select any space adjacent to M26 pieces.
        # Sierra Maestra (11) is adjacent to Oriente (9) and Santiago De Cuba (12).
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        mask = self.env.legal_actions

        self.assertEqual(mask[self.env._ops_action_base + OP_MARCH_M26 * 13 + 9], 1)
        self.assertEqual(mask[self.env._ops_action_base + OP_MARCH_M26 * 13 + 12], 1)

        # 2. Check that LimOp allows choosing one destination.
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        mask_lim = self.env.legal_actions
        self.assertEqual(mask_lim[self.env._limited_ops_action_base + OP_MARCH_M26 * 13 + 9], 1)
        self.assertEqual(mask_lim[self.env._limited_ops_action_base + OP_MARCH_M26 * 13 + 12], 1)

        # But once one is picked (e.g. 9), the system only allows sources that can reach 9.
        self.env.step(self.env._limited_ops_action_base + OP_MARCH_M26 * 13 + 9)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_op_target['dest'], 9)
        # In TARGET_SPACE phase, user picks sources. Rule says "all end in a single destination".
        # This is enforced because only one 'dest' is in pending_op_target.

    def test_resource_phase_govt_earnings(self):
        """
        Rule 6.2.1: Govt earnings include unsabotaged ECs + Aid.
        ECs Sabotaged if insurgents > cubes.
        """
        # Setup: Cigar EC (1) with 2 M26, 1 Govt. Should be Sabotaged.
        # Textile EC (6) with 0 M26, 0 Govt. Should NOT be Sabotaged.
        # Sugar Cane EC (10) with 1 M26, 2 Govt. Should NOT be Sabotaged.
        # Aid = 15.
        self.env.board.spaces[1].pieces[2] = 2
        self.env.board.spaces[1].pieces[0] = 1

        self.env.board.spaces[10].pieces[2] = 1
        self.env.board.spaces[10].pieces[0] = 2

        self.env.set_aid(15)
        self.env.players[0].resources = 10

        self.env._propaganda_resources_phase()

        # Earnings:
        # Cigar EC (1): Sabotaged (2 > 1). Econ 3.
        # Textile EC (6): Not Sabotaged. Econ 3.
        # Sugar Cane EC (10): Not Sabotaged. Econ 2.
        # Total unsabotaged Econ = 3 (6) + 2 (10) = 5.
        # Income = 5 + 15 (Aid) = 20.
        # Total Govt resources = 10 + 20 = 30.
        self.assertTrue(self.env.board.spaces[1].sabotage)
        self.assertFalse(self.env.board.spaces[6].sabotage)
        self.assertFalse(self.env.board.spaces[10].sabotage)
        self.assertEqual(self.env.players[0].resources, 30)

    def test_resource_phase_insurgent_earnings(self):
        """
        Rule 6.2.2:
        M26: number of Bases.
        DR: number of spaces with pieces.
        Syndicate: Pop/Econ where Syn > Police, plus 2x open Casinos.
        """
        # M26: 2 Bases (in 11 and 5)
        self.env.board.spaces[11].pieces[4] = 1
        self.env.board.spaces[5].pieces[4] = 1

        # DR: pieces in 3 spaces (0, 4, 7)
        self.env.board.spaces[0].pieces[5] = 1
        self.env.board.spaces[4].pieces[6] = 1
        self.env.board.spaces[7].pieces[7] = 1

        # Syndicate: Havana (3) Syn G (2) > Police (1). Pop 6.
        # Sugar Cane EC (10): Syn G (1) <= Police (1). Econ 0.
        # Open Casinos: 3 total (3, 5, 8).
        self.env.board.spaces[3].pieces[8] = 2
        self.env.board.spaces[3].pieces[1] = 1
        self.env.board.spaces[10].pieces[8] = 1
        self.env.board.spaces[10].pieces[1] = 1
        self.env.board.spaces[3].pieces[10] = 1
        self.env.board.spaces[5].pieces[10] = 1
        self.env.board.spaces[8].pieces[10] = 1

        self.env.players[1].resources = 0
        self.env.players[2].resources = 0
        self.env.players[3].resources = 10 # Start with some to test Skim

        self.env._refresh_campaign_tracks()
        self.env._propaganda_resources_phase()

        self.assertEqual(self.env.players[1].resources, 2)
        self.assertEqual(self.env.players[2].resources, 3)
        # Syn Income Calculation:
        # - Havana (3): Pop 6 (Syn G > Police).
        # - EC 10: 0 (Syn G <= Police).
        # - Open Casinos: 2 * 3 = 6.
        # Total Income = 6 + 6 = 12.
        # Skim:
        # - Havana (3): Syn G(2) + C(1) = 3 total Syn vs 1 Govt. Syn Controls. No skim.
        # - Space 5: Syn C(1) vs M26 B(1). Tied (0 total). No one controls. No skim.
        # - Space 8: Syn C(1). Syn controls. No skim.
        # Total Syn Resources = 10 (start) + 12 (income) = 22.
        self.assertEqual(self.env.players[3].resources, 22)

    def test_cash_deposits_propaganda(self):
        """
        Rule 6.2.4: Cash removed for +6 resources or a Base.
        """
        # Setup: M26 has 1 cash in Sierra Maestra (11). No Bases available.
        # Syndicate has 1 cash in Havana (3). Has Bases available.
        self.env.board.spaces[11].pieces[2] = 1 # M26 UG
        self.env.board.spaces[11].cash_holders[2] = 1
        self.env.players[1].available_bases = 0
        self.env.players[1].resources = 10

        self.env.board.spaces[3].pieces[8] = 1 # Syn UG
        self.env.board.spaces[3].cash_holders[8] = 1
        self.env.players[3].available_bases = 5
        self.env.players[3].resources = 10

        self.env.board.spaces[11].refresh_cash_counts()
        self.env.board.spaces[3].refresh_cash_counts()
        self.env._refresh_campaign_tracks()

        self.env._propaganda_resources_phase()

        # M26 should get +6 resources.
        self.assertEqual(self.env.players[1].resources, 16)
        # Syndicate should get a Base (Casino) in Havana.
        self.assertEqual(self.env.board.spaces[3].pieces[10], 1)
        self.assertEqual(self.env.players[3].available_bases, 4)
        # Havana Pop=6. Syn G (1) > Police (0). Earnings = 6.
        # Total resources = 10 + 6 = 16.
        self.assertEqual(self.env.players[3].resources, 16)

    def test_kidnap_special_activity(self):
        """
        Rule 4.3.3: Kidnap removes Resources from Govt/Syn and closes Casino.
        """
        # Ensure only M26 is eligible for turn order consistency
        for i in [0, 2, 3]: self.env.players[i].eligible = False
        self.env.update_turn_pointer()

        # Setup: Havana (3) with 2 M26 UG, 1 Police, 1 open Casino.
        space = self.env.board.spaces[3]
        space.pieces[2] = 2 # M26 UG
        space.pieces[1] = 1 # Police
        space.pieces[10] = 1 # open Casino
        space.update_control()

        self.env.players[1].resources = 10
        self.env.players[0].resources = 10
        self.env.current_player_num = 1 # M26

        # 1. Choose Ops: Terror
        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.env.step(self.env._ops_action_base + OP_TERROR_M26 * 13 + 3)

        # 2. Choose Special Activity: Kidnap
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        action_idx = self.env._ops_action_base + OP_KIDNAP_M26 * 13 + 3
        # Since Govt and Syn pieces are present, it should pause for target faction selection.
        self.env.step(action_idx)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        # Select Govt (0)
        self.env.step(self.env._target_faction_action_base + 0)

        # Verification:
        # Kidnap activates 1 UG. Terror activated another 1 UG.
        # Total pieces[3] (Active) should be 2.
        self.assertEqual(space.pieces[3], 2)
        # Casino should be closed.
        self.assertEqual(space.pieces[10], 0)
        self.assertEqual(space.closed_casinos, 1)
        # Resources should be transferred (roll-based, but >0).
        self.assertTrue(self.env.players[0].resources < 10 or self.env.players[1].resources > 10)

    def test_assassinate_special_activity(self):
        """
        Rule 4.4.3: Assassinate removes ANY 1 enemy piece in DR Terror space where DR > Police.
        """
        # Ensure only DR is eligible for turn order consistency
        for i in [0, 1, 3]: self.env.players[i].eligible = False
        self.env.update_turn_pointer()

        # Setup: Havana (3) with 2 DR UG, 1 Police, 1 Govt Base.
        space = self.env.board.spaces[3]
        space.pieces[5] = 2 # DR UG
        space.pieces[1] = 1 # Police
        space.govt_bases = 1
        space.alignment = 1 # Passive Support
        space.support_active = False
        space.update_control()

        self.env.players[2].resources = 10
        self.env.current_player_num = 2 # DR

        # 1. Choose Ops: Terror
        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.env.step(self.env._ops_action_base + OP_TERROR_DR * 13 + 3)

        # 2. Choose Special Activity: Assassinate
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        action_idx = self.env._ops_action_base + OP_ASSASSINATE_DR * 13 + 3

        self.env.step(action_idx)

        # Verification:
        # Terror should activate 1 UG.
        self.assertEqual(space.pieces[5], 1)
        self.assertEqual(space.pieces[6], 1)
        # Terror should shift alignment toward Neutral (from Passive Support).
        self.assertEqual(space.alignment, 0)

        # Assassinate in this setup had 2 choices (Police index 1 or Base index 2).
        # It should be in PHASE_CHOOSE_EVENT_OPTION.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        # Select Base (2)
        self.env.step(self.env._event_option_action_base + 2)

        # Assassinate should remove Govt Base.
        self.assertEqual(space.govt_bases, 0)
        self.assertEqual(self.env.players[0].available_bases, 4)

    def test_pact_of_caracas_cancel(self):
        """
        Rule 5.3 (Event 18): removal of 2 bases at once cancels Capability.
        """
        self.env.capabilities.add("PactOfCaracas_Unshaded")
        self.env.current_player_num = 0 # Govt
        # Must initialize tracking since we're starting mid-turn
        self.env._begin_pact_action_tracking()

        # Setup: Las Villas (5) with 2 M26 Bases.
        self.env.board.spaces[5].pieces[4] = 2
        self.env.board.spaces[5].pieces[0] = 5 # Plenty of troops
        self.env.board.spaces[5].update_control()

        # Govt Assaults M26 in Las Villas
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        action = self.env._ops_action_base + OP_ASSAULT * 13 + 5
        self.env.step(action)

        # Verification: Pact should be gone
        self.assertNotIn("PactOfCaracas_Unshaded", self.env.capabilities)

    def test_sim_shaded_capability(self):
        """
        Rule 5.4 (Event 4): Police Sweep and Assault as if Troops.
        """
        self.env.capabilities.add("SIM_Shaded")
        self.env.current_player_num = 0 # Govt

        # 1. Test Sweep: Police should move from adjacent.
        # Havana (3) selected for Sweep. La Habana (2) has Police.
        self.env.board.spaces[2].pieces[1] = 2
        self.env.board.spaces[3].update_control()

        self.env.phase = PHASE_CHOOSE_OP_ACTION
        # Choose Sweep in Havana
        self.env.step(self.env._ops_action_base + OP_SWEEP * 13 + 3)

        # Should be in PHASE_CHOOSE_TARGET_SPACE to pick source
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        # Select source La Habana (2)
        self.env.step(self.env._target_space_action_base + 2)
        # Choose piece type Police (1)
        self.env.step(self.env._event_option_action_base + 1)
        # Choose count 2 (1)
        self.env.step(self.env._event_option_action_base + 1)

        # Finish Sweep
        self.env.step(self.env._main_action_base + MAIN_PASS)

        # Verification: Police moved to Havana
        self.assertEqual(self.env.board.spaces[3].pieces[1], 2)

        # 2. Test Assault: Police in Forest should remove Active piece.
        # Pinar Del Rio (0) is Forest. Has 2 Police, 1 M26 Active.
        self.clear_board()
        self.env.capabilities.add("SIM_Shaded")
        self.env.board.spaces[0].pieces[1] = 2
        self.env.board.spaces[0].pieces[3] = 1
        self.env.board.spaces[0].update_control()

        self.env.current_player_num = 0
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        # Choose Assault in Pinar Del Rio
        self.env.step(self.env._ops_action_base + OP_ASSAULT * 13 + 0)

        # Verification: M26 Active should be removed (Police acts as Troop).
        self.assertEqual(self.env.board.spaces[0].pieces[3], 0)

    def test_march_activation_detailed(self):
        """
        Rule 3.3.2: Activate if moving group + cubes > 3.
        """
        # Ensure only M26 is eligible for turn order consistency
        for i in [0, 2, 3]: self.env.players[i].eligible = False
        self.env.update_turn_pointer()

        # Setup: Sierra Maestra (11) with 2 M26 UG.
        # Oriente (9) with 2 Govt Troops. Oriente is Forest.
        # Oriente pop=2.
        # Set Oriente to Passive Support so it meets the alignment condition
        self.env.board.spaces[9].alignment = 1
        self.env.board.spaces[9].support_active = False
        self.env.board.spaces[11].pieces[2] = 2
        self.env.board.spaces[9].pieces[0] = 2
        self.env.board.spaces[9].update_control()

        self.env.players[1].resources = 10
        self.env.current_player_num = 1 # M26

        # 1. Choose Ops: March to Oriente
        self.env.step(self.env._main_action_base + MAIN_OPS)
        # Select destination Oriente (9)
        self.env.step(self.env._ops_action_base + OP_MARCH_M26 * 13 + 9)

        # 2. Select source Sierra Maestra (11)
        # Piece 1
        self.env.step(self.env._target_space_action_base + 11)

        # Piece 2
        self.env.step(self.env._target_space_action_base + 11)

        # Finish March
        self.env.step(self.env._main_action_base + MAIN_PASS)

        # Verification:
        # Moving group (2) + Cubes in Oriente (2) = 4.
        # 4 > 3, so they should ACTIVATE.
        self.assertEqual(self.env.board.spaces[9].pieces[2], 0, "Guerrillas should be active")
        self.assertEqual(self.env.board.spaces[9].pieces[3], 2)

    def test_airstrike_priority(self):
        """
        Rule 4.2.2: Air Strike removes Active Guerrilla first.
        If no Guerrillas, then Base.
        """
        # Setup: Oriente (9) with 1 M26 Base and 1 M26 Active.
        space = self.env.board.spaces[9]
        space.pieces[4] = 1 # Base
        space.pieces[3] = 1 # Active
        space.update_control()

        self.env.current_player_num = 0 # Govt
        # 1. First Air Strike should hit Active
        self.env.op_airstrike(9)
        self.assertEqual(space.pieces[3], 0, "Active Guerrilla should be removed first")
        self.assertEqual(space.pieces[4], 1, "Base should be protected if Active is present")

        # 2. Second Air Strike should hit Base
        self.env.op_airstrike(9)
        self.assertEqual(space.pieces[4], 0, "Base should be removed if no Guerrillas left")

    def test_ambush_bases_last(self):
        """
        Rule 4.3.2: Ambush removes pieces normally (Bases Last).
        """
        # Setup: Las Villas (5) with 1 Govt Base, 2 Police, 1 M26 UG.
        space = self.env.board.spaces[5]
        space.govt_bases = 1
        space.pieces[1] = 2 # 2 Police
        space.pieces[2] = 1 # M26 UG
        space.update_control()

        self.env.current_player_num = 1 # M26
        # Ambush in Las Villas
        self.env.op_ambush_m26(5)

        # Verification: 2 removals should hit 2 Police, Base remains.
        self.assertEqual(space.pieces[1], 0, "Both Police should be removed")
        self.assertEqual(space.govt_bases, 1, "Base should be protected by Police (Bases Last)")

    def test_garrison_activation_ec(self):
        """
        Rule 3.2.2: Garrison activates 1 Guerrilla for each cube in EC.
        """
        # Ensure only GOVT is eligible for turn order consistency
        for i in [1, 2, 3]: self.env.players[i].eligible = False
        self.env.update_turn_pointer()

        # Setup: Cigar EC (1) with 2 M26 UG, 1 Govt Troop.
        # Garrison destination will have 2 cubes total (move 1 police).
        space = self.env.board.spaces[1]
        space.pieces[2] = 2 # M26 UG
        space.pieces[0] = 1 # Govt Troop
        # Neighbor La Habana (2) is adjacent to Cigar EC (1)
        self.env.board.spaces[2].pieces[1] = 1
        self.env.board.spaces[3].update_control()

        self.env.current_player_num = 0 # Govt
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        # 1. Start Garrison in Cigar EC
        self.env.step(self.env._ops_action_base + OP_GARRISON * 13 + 1)

        # 2. Pick source La Habana (2)
        self.env.step(self.env._target_space_action_base + 2)
        # 3. Pick count 1
        self.env.step(self.env._event_option_action_base + 0)

        # 4. Finish Garrison
        self.env.step(self.env._main_action_base + MAIN_PASS)

        # Verification: 2 cubes in EC (1 Troop + 1 Police moved).
        # So 2 Guerrillas should be activated.
        self.assertEqual(space.pieces[2], 0, "Both guerrillas should be activated by 2 cubes")
        self.assertEqual(space.pieces[3], 2)

    def test_transport_source_restriction(self):
        """
        Rule 4.2.1: Transport from City or Base only.
        """
        # Setup:
        # Pinar del Rio (0): Province, 2 Troops, NO Base.
        # Havana (3): City, 0 Troops.
        self.env.board.spaces[0].pieces[0] = 2
        self.env.board.spaces[3].pieces[0] = 0

        # Action: Transport into Havana
        self.env.current_player_num = 0 # Govt
        self.env.op_transport(3)

        # Verification: No troops should have moved from Pinar del Rio as it's not a City/Base.
        self.assertEqual(self.env.board.spaces[3].pieces[0], 0, "Troops should not move from non-City/Base space")

        # Now add a Base to Pinar del Rio
        self.env.board.spaces[0].govt_bases = 1
        self.env.op_transport(3)
        self.assertEqual(self.env.board.spaces[3].pieces[0], 2, "Troops should move from space with Base")

    def test_syn_rally_flip(self):
        """
        Rule 3.3.1: Syndicate Rally can flip all guerrillas underground if Casino present.
        """
        # Setup: Havana (3) with 2 Syndicate Active, 1 open Casino.
        space = self.env.board.spaces[3]
        space.pieces[9] = 2 # Syn Active
        space.pieces[10] = 1 # Open Casino

        self.env.current_player_num = 3 # Syndicate
        # Rally in Havana
        self.env.op_rally_syn(3, force_flip=True)

        # Verification: All should be Underground.
        self.assertEqual(space.pieces[9], 0)
        self.assertEqual(space.pieces[8], 2)

    def test_syn_construct_control_restriction(self):
        """
        Rule 3.3.5: Construct only in City/Province with Govt or Syn Control.
        """
        # Setup: Oriente (9) is a Province. M26 Controls (index 1).
        space = self.env.board.spaces[9]
        space.pieces[2] = 5 # M26 control
        space.update_control()
        self.assertEqual(space.controlled_by, 2)

        self.env.current_player_num = 3 # Syndicate
        self.env.players[3].resources = 10
        self.env.players[3].available_bases = 5
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        mask = self.env.legal_actions
        action_idx = self.env._ops_action_base + OP_CONSTRUCT_SYN * 13 + 9
        self.assertEqual(mask[action_idx], 0, "Construct should be illegal in M26 controlled space")

        # Add Govt cubes for Govt control
        space.pieces[0] = 10
        space.update_control()
        self.assertEqual(space.controlled_by, 1)
        mask = self.env.legal_actions
        self.assertEqual(mask[action_idx], 1, "Construct should be legal in Govt controlled space")

if __name__ == '__main__':
    unittest.main()
