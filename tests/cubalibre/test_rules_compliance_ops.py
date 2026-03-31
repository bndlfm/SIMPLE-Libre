import unittest
import numpy as np
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_MAIN,
    MAIN_OPS,
    MAIN_PASS,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_EVENT_OPTION
)

class TestRulesComplianceOps(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=42)
        # Clear the board for deterministic testing
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.update_control()

    def _setup_player(self, player_num, resources=10, eligible=True):
        self.env.current_player_num = player_num
        self.env.players[player_num].eligible = eligible
        self.env.players[player_num].resources = resources
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

    def _enter_ops(self):
        enter_ops = self.env._main_action_base + MAIN_OPS
        self.env.step(enter_ops)

    def test_m26_rally_capacity_rules_3_3_1(self):
        """Rule 3.3.1: M26 Rally capacity is 2 * (Bases + Pop)."""
        self._setup_player(1) # M26
        lv_id = 5 # Las Villas: Pop 2
        self.env.board.spaces[lv_id].pieces[4] = 1 # 1 Base
        self.env.players[1].available_forces[0] = 10 # 10 Guerrillas available

        self._enter_ops()
        # op_rally_m26 = 7
        a = self.env._ops_action_base + 7 * self.env.num_spaces + lv_id
        self.env.step(a)

        # Expected: 2 * (2 pop + 1 base) = 6 guerrillas placed
        # Current implementation likely only places 2 + 1 = 3
        self.assertEqual(int(self.env.board.spaces[lv_id].pieces[2]), 6,
                         "M26 Rally should place 2 * (Pop + Bases) guerrillas.")

    def test_syndicate_rally_capacity_rules_3_3_1(self):
        """Rule 3.3.1 & Playbook: Syndicate Rally places only single Guerrillas."""
        self._setup_player(3) # Syndicate
        havana_id = 3 # Havana: Pop 6
        self.env.board.spaces[havana_id].pieces[10] = 1 # 1 Casino
        self.env.players[3].available_forces[0] = 10

        self._enter_ops()
        # op_rally_syn = 18
        a = self.env._ops_action_base + 18 * self.env.num_spaces + havana_id
        self.env.step(a)

        # Expected: 1 guerrilla placed
        # Current implementation likely incorrectly uses pop + bases = 7
        self.assertEqual(int(self.env.board.spaces[havana_id].pieces[8]), 1,
                         "Syndicate Rally should only place a single guerrilla.")

    def test_m26_ambush_targets_other_insurgents_and_adds_guerrilla_rule_4_3_2(self):
        """Rule 4.3.2: Ambush targets any enemy and adds an available guerrilla."""
        self._setup_player(1) # M26
        sierra_id = 11
        self.env.board.spaces[sierra_id].pieces[2] = 1 # 1 UG M26 for Ambush
        self.env.board.spaces[sierra_id].pieces[5] = 2 # 2 UG DR as targets
        self.env.players[1].available_forces[0] = 1 # 1 Guerrilla available to be added

        self._enter_ops()
        # op_attack_m26 = 9
        a = self.env._ops_action_base + 9 * self.env.num_spaces + sierra_id
        self.env.step(a)

        # If it prompts for SA
        if self.env.phase == PHASE_CHOOSE_SPECIAL_ACTIVITY:
            # op_ambush_m26 = 13
            sa = self.env._ops_action_base + 13 * self.env.num_spaces + sierra_id
            self.env.step(sa)

        # Expected:
        # 1. 2 DR guerrillas removed (if targeted)
        # 2. 1 M26 guerrilla added (from available to UG)
        # Current implementation:
        # 1. Only targets Govt (hardcoded)
        # 2. Doesn't add piece
        self.assertEqual(int(self.env.board.spaces[sierra_id].pieces[5]), 0,
                         "Ambush should be able to target and remove DR guerrillas.")
        self.assertEqual(int(self.env.board.spaces[sierra_id].pieces[2]), 2,
                         "Ambush should add an available guerrilla to the space.")

    def test_dr_assassinate_targets_bases_rule_4_4_3(self):
        """Rule 4.4.3: Assassinate removes ANY 1 enemy piece (including bases)."""
        self._setup_player(2) # DR
        havana_id = 3
        self.env.board.spaces[havana_id].pieces[5] = 2 # 2 UG DR for Terror/Assassinate
        self.env.board.spaces[havana_id].pieces[10] = 1 # Syndicate Casino
        self.env.players[3].available_bases = 9 # So we can see it returned if removed

        self._enter_ops()
        # op_terror_dr = 16
        a = self.env._ops_action_base + 16 * self.env.num_spaces + havana_id
        self.env.step(a)

        # Expected to prompt for SA
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        # op_assassinate_dr = 17
        sa = self.env._ops_action_base + 17 * self.env.num_spaces + havana_id
        self.env.step(sa)

        # If multiple enemy factions, it should transition to PHASE_CHOOSE_TARGET_FACTION
        if self.env.phase == PHASE_CHOOSE_TARGET_FACTION:
            # target Syndicate = 3
            self.env.step(self.env._target_faction_action_base + 3)

        # Then possibly piece type if multiple types
        if self.env.phase == PHASE_CHOOSE_EVENT_OPTION:
             # target Base = 2
             self.env.step(self.env._event_option_action_base + 2)

        # Expected: Casino closed (Rules 1.4.5: close instead of remove)
        self.assertEqual(int(self.env.board.spaces[havana_id].pieces[10]), 0)
        self.assertEqual(self.env.board.spaces[havana_id].closed_casinos, 1,
                         "Assassinate should be able to close a Casino.")

    def test_syndicate_bribe_removes_pieces_rule_4_5_4(self):
        """Rule 4.5.4: Bribe removes or flips pieces at cost of 3 resources."""
        self._setup_player(3) # Syndicate
        self.env.players[3].resources = 10
        havana_id = 3
        self.env.board.spaces[havana_id].pieces[0] = 2 # 2 Govt Troops

        self._enter_ops()
        # Any op to enable SA, e.g. Rally = 18
        a = self.env._ops_action_base + 18 * self.env.num_spaces + havana_id
        self.env.step(a)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        # op_bribe_syn = 22
        sa = self.env._ops_action_base + 22 * self.env.num_spaces + havana_id
        self.env.step(sa)

        # Current implementation incorrectly transfers 2 resources from Govt.
        # It should prompt for targets and deduct 3 resources.

        # If it correctly transitions to target selection
        if self.env.phase == PHASE_CHOOSE_TARGET_FACTION:
            self.env.step(self.env._target_faction_action_base + 0) # Govt

        if self.env.phase == PHASE_CHOOSE_EVENT_OPTION:
            self.env.step(self.env._event_option_action_base + 0) # Troops

        self.assertEqual(self.env.players[3].resources, 10 - 1 - 3,
                         "Bribe should cost 3 resources plus 1 for the Rally.")
        self.assertEqual(int(self.env.board.spaces[havana_id].pieces[0]), 0,
                         "Bribe should remove target pieces.")

if __name__ == "__main__":
    unittest.main()
