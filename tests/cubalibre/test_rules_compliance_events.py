import unittest
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_MAIN,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_EVENT_OPTION
)
from app.environments.cubalibre.envs.classes import Card

class TestRulesComplianceEvents(unittest.TestCase):
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

    def _setup_card(self, card_id):
        # Force a specific card
        from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])
        # Set first eligible player based on card order
        self.env.current_player_num = self.env.current_card.faction_order[0]
        self.env.players[self.env.current_player_num].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

    def test_card_19_manifesto_faction_order_rules_5_1(self):
        """Card 19 Manifesto: In card Faction order, each Faction may place 2 non-Casino pieces."""
        self._setup_card(19)
        order = self.env.current_card.faction_order

        for f in range(4):
            self.env.board.add_piece(3, f, 0) # Havana
            self.env.players[f].available_forces[0] = 10
            self.env.players[f].available_bases = 5

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        for f_idx in order:
            self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
            pending_f = self.env._pending_event_target["f_idx"]
            self.assertEqual(pending_f, f_idx, f"Faction {f_idx} should be acting in Manifesto order.")

            for i in range(2):
                self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
                self.env.step(self.env._target_space_action_base + 3)
                if self.env.phase == PHASE_CHOOSE_EVENT_OPTION:
                    self.env.step(self.env._event_option_action_base + 0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertEqual(self.env.card_action_slot, 1)

    def test_card_44_rebel_air_force_unshaded_target_choice_rule_5_1(self):
        """Card 44 Rebel Air Force (Un): 26July or DR free Ambushes Government forces."""
        self._setup_card(44)
        self.env.board.spaces[3].pieces[0] = 5 # Troops in Havana
        self.env.board.add_piece(3, 1, 0)
        self.env.board.add_piece(3, 2, 0)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.env.step(self.env._target_faction_action_base + 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 3)

        self.assertEqual(int(self.env.board.spaces[3].pieces[0]), 3, "Ambush should remove 2 Govt troops.")

    def test_card_1_armored_cars_unshaded_target_choice_rule_5_1(self):
        """Card 1 Armored Cars (Un): 26July or DR free Marches into a space and free Ambushes there."""
        self._setup_card(1)
        self.env.board.add_piece(2, 1, 0) # M26 in La Habana
        self.env.board.add_piece(3, 2, 0) # DR in Havana (target)
        self.env.board.add_piece(3, 2, 0)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.env.step(self.env._target_faction_action_base + 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 3)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 2)

        if self.env.phase == PHASE_CHOOSE_TARGET_FACTION:
            self.env.step(self.env._target_faction_action_base + 2)

        self.assertEqual(int(self.env.board.spaces[3].pieces[5]), 0, "Armored Cars Ambush should be able to remove DR pieces.")

if __name__ == "__main__":
    unittest.main()

    def test_card_33_carlos_prio_unshaded_faction_choice_rule_5_1(self):
        """Card 33 Carlos Prío (Un): +5 DR or +5 M26 Resources."""
        # Test M26 choice
        self._setup_card(33)
        self.env.players[1].resources = 10
        self.env.players[2].resources = 10

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.env.step(self.env._target_faction_action_base + 1) # M26

        self.assertEqual(self.env.players[1].resources, 15)
        self.assertEqual(self.env.players[2].resources, 10)

    def test_card_29_faure_chomon_unshaded_faction_choice_rule_5_1(self):
        """Card 29 Fauré Chomón (Un): DR or 26July places a Base and 2 Guerrillas in Las Villas."""
        # Test M26 choice
        self._setup_card(29)
        self.env.players[1].available_bases = 5
        self.env.players[1].available_forces[0] = 10

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.env.step(self.env._target_faction_action_base + 1) # M26

        lv = self.env.board.spaces[5]
        self.assertEqual(int(lv.pieces[4]), 1) # M26 Base
        self.assertEqual(int(lv.pieces[2]), 2) # M26 UG
