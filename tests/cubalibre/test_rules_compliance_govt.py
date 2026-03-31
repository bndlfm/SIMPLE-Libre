import unittest
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_MAIN,
    MAIN_OPS,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    US_ALLIANCE_FIRM,
    US_ALLIANCE_RELUCTANT,
    US_ALLIANCE_EMBARGOED
)

class TestRulesComplianceGovt(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=42)
        # Clear the board
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.update_control()

    def _setup_govt(self, resources=20, alliance=US_ALLIANCE_FIRM):
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = resources
        self.env.set_us_alliance(alliance)
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

    def _enter_ops(self):
        enter_ops = self.env._main_action_base + MAIN_OPS
        self.env.step(enter_ops)

    def test_assault_prompts_for_target_faction_rules_3_1(self):
        """Rule 3.1: The executing Faction chooses the enemy Factions to be targeted."""
        self.env.manual = True
        self._setup_govt()
        havana_id = 3
        self.env.board.spaces[havana_id].pieces[0] = 5 # Troops
        self.env.board.spaces[havana_id].pieces[3] = 1 # Active M26
        self.env.board.spaces[havana_id].pieces[6] = 1 # Active DR

        self._enter_ops()
        # op_assault = 4
        a = self.env._ops_action_base + 4 * self.env.num_spaces + havana_id
        self.env.step(a)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION,
                         "Assault should prompt for target faction when multiple enemies are present.")
        self.assertIn(1, self.env._pending_event_faction["allowed"])
        self.assertIn(2, self.env._pending_event_faction["allowed"])

    def test_sweep_reveals_multiple_factions_rules_3_2_3(self):
        """Rule 3.2.3: Sweep activates 1 Guerrilla for each cube there."""
        self._setup_govt()
        havana_id = 3
        self.env.board.spaces[havana_id].pieces[0] = 2 # 2 Troops
        self.env.board.spaces[havana_id].pieces[2] = 1 # UG M26
        self.env.board.spaces[havana_id].pieces[5] = 1 # UG DR

        self._enter_ops()
        # op_sweep = 3
        a = self.env._ops_action_base + 3 * self.env.num_spaces + havana_id
        self.env.step(a)

        # Expected: Both revealed because budget (2 cubes) >= total UG (2)
        self.assertEqual(int(self.env.board.spaces[havana_id].pieces[3]), 1, "M26 should be revealed.")
        self.assertEqual(int(self.env.board.spaces[havana_id].pieces[6]), 1, "DR should be revealed.")

    def test_us_alliance_impacts_op_costs_rules_6_3_1(self):
        """Rule 6.3.1: US Alliance level affects COIN Operation costs."""
        # Firm: 2 resources
        self._setup_govt(alliance=US_ALLIANCE_FIRM)
        self.env.board.spaces[3].pieces[0] = 1
        self._enter_ops()
        self.env.step(self.env._ops_action_base + 0 * self.env.num_spaces + 3) # Train
        self.assertEqual(self.env.players[0].resources, 20 - 2)

        # Reluctant: 3 resources
        self.env.reset(seed=42)
        self._setup_govt(alliance=US_ALLIANCE_RELUCTANT)
        self.env.board.spaces[3].pieces[0] = 1
        self._enter_ops()
        self.env.step(self.env._ops_action_base + 0 * self.env.num_spaces + 3) # Train
        self.assertEqual(self.env.players[0].resources, 20 - 3)

        # Embargoed: 4 resources
        self.env.reset(seed=42)
        self._setup_govt(alliance=US_ALLIANCE_EMBARGOED)
        self.env.board.spaces[3].pieces[0] = 1
        self._enter_ops()
        self.env.step(self.env._ops_action_base + 0 * self.env.num_spaces + 3) # Train
        self.assertEqual(self.env.players[0].resources, 20 - 4)

    def test_air_strike_availability_rules_6_3_1(self):
        """Rule 6.3.1: No Air Strikes if US Alliance is Embargoed."""
        # Firm: Air Strike available
        self._setup_govt(alliance=US_ALLIANCE_FIRM)
        lv_id = 5 # Las Villas (Province)
        self.env.board.spaces[lv_id].pieces[0] = 1 # Troops for Sweep
        self.env.board.spaces[lv_id].pieces[3] = 1 # Active M26 for Air Strike

        self._enter_ops()
        # op_sweep = 3
        self.env.step(self.env._ops_action_base + 3 * self.env.num_spaces + lv_id)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        # op_airstrike = 6
        airstrike_action = self.env._ops_action_base + 6 * self.env.num_spaces + lv_id
        self.assertEqual(self.env.legal_actions[airstrike_action], 1, "Air Strike should be legal when Firm.")

        # Embargoed: Air Strike NOT available
        self.env.reset(seed=42)
        self._setup_govt(alliance=US_ALLIANCE_EMBARGOED)
        self.env.board.spaces[lv_id].pieces[0] = 1
        self.env.board.spaces[lv_id].pieces[3] = 1
        self._enter_ops()
        self.env.step(self.env._ops_action_base + 3 * self.env.num_spaces + lv_id)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        airstrike_action = self.env._ops_action_base + 6 * self.env.num_spaces + lv_id
        # Note: LegalActionsMixin uses sa_air_strike_embargo_block. Let's check it.
        self.assertEqual(self.env.legal_actions[airstrike_action], 0, "Air Strike should be illegal when Embargoed.")

if __name__ == "__main__":
    unittest.main()
