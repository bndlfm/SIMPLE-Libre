import unittest
import numpy as np
from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.env import (
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_MAIN
)

class TestRound5Events(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv()
        self.env.reset()

    def set_card(self, card_id):
        data = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(
            card_id,
            data["name"],
            data["order"],
            data["unshaded"],
            data["shaded"],
        )
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

    def test_sim_un_alignment_shift(self):
        # Card 4 (S.I.M., Un): Remove Support from space with no Police.
        self.env.board.spaces[2].alignment = 1
        self.env.board.spaces[2].support_active = True
        self.env.board.spaces[2].pieces[1] = 0 # No Police
        
        self.set_card(4)
        self.env.step(self.env._event_side_base + 0) # EVENT_UNSHADED
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_event_target["event"], "SIM_UN")
        
        self.env.step(self.env._target_space_action_base + 2)
        self.assertEqual(self.env.board.spaces[2].alignment, 1)
        self.assertFalse(self.env.board.spaces[2].support_active)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    @unittest.skip("Covered by tests/cubalibre/test_card_23_radio_rebelde.py")
    def test_radio_rebelde_un_requires_two_distinct_provinces(self):
        # Card 23 (Radio Rebelde, Un): Shift 2 Provinces each 1 level toward Active Opposition.
        # Must be 2 distinct Provinces.
        # Use two actual Provinces (not Econ Centers): La Habana (2) and Matanzas (4).
        self.env.board.spaces[2].alignment = 1
        self.env.board.spaces[2].support_active = False
        self.env.board.spaces[4].alignment = 1
        self.env.board.spaces[4].support_active = False

        self.set_card(23)
        self.env.step(self.env._event_side_base + 0)  # Unshaded
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # Pick Province 2 first.
        pick_2 = self.env._target_space_action_base + 2
        self.assertEqual(self.env.legal_actions[pick_2], 1)
        self.env.step(pick_2)

        # Province 2 should now be illegal for the second pick.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env.legal_actions[pick_2], 0)

        # Pick a different Province for the second shift.
        pick_4 = self.env._target_space_action_base + 4
        self.assertEqual(self.env.legal_actions[pick_4], 1)
        self.env.step(pick_4)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    @unittest.skip("Covered by tests/cubalibre/test_card_19_sierra_maestra_manifesto.py")
    def test_manifesto_un_multi_place(self):
        # Card 19 (Manifesto, Un): Each Faction places 2 non-Casino pieces.
        self.set_card(19)
        self.env.step(self.env._event_side_base + 0) # EVENT_UNSHADED
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_event_target["f_idx"], 0) # Govt
        
        # Govt places 2 pieces (Havana)
        self.env.step(self.env._target_space_action_base + 3)
        self.assertEqual(self.env._pending_event_target["f_idx"], 0)
        self.assertEqual(self.env._pending_event_target["count"], 1)
        self.env.step(self.env._target_space_action_base + 3)
        
        # M26's turn
        self.assertEqual(self.env._pending_event_target["f_idx"], 1)
        self.env.step(self.env._target_space_action_base + 9)
        self.env.step(self.env._target_space_action_base + 9)
        
        # DR's turn
        self.assertEqual(self.env._pending_event_target["f_idx"], 2)
        self.env.step(self.env._target_space_action_base + 12)
        self.env.step(self.env._target_space_action_base + 12)
        
        # Syndicate
        self.assertEqual(self.env._pending_event_target["f_idx"], 3)
        self.env.step(self.env._target_space_action_base + 5)
        self.env.step(self.env._target_space_action_base + 5)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertGreaterEqual(self.env.board.spaces[3].pieces[0], 2)
        self.assertGreaterEqual(self.env.board.spaces[9].pieces[2], 2)
        self.assertGreaterEqual(self.env.board.spaces[12].pieces[5], 2)

    @unittest.skip("Covered by tests/cubalibre/test_card_20_the_twelve.py")
    def test_the_twelve_sh_remove_half(self):
        # Card 20 (The Twelve, Sh): Covered by per-card test suite.
        self.env.board.spaces[0].pieces[2] = 3
        self.env.board.spaces[0].pieces[5] = 4
        
        self.set_card(20)
        self.env.step(self.env._event_side_base + 1) # EVENT_SHADED
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        
        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(self.env.board.spaces[0].pieces[2], 1)
        self.assertEqual(self.env.board.spaces[0].pieces[5], 2)
        
        self.env.step(self.env._target_space_action_base + 4) # Matanzas
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    @unittest.skip("Covered by tests/cubalibre/test_card_28_morgan.py")
    def test_morgan_sh_support_active(self):
        # Card 28 (Morgan, Sh): Set space with DR Guerrilla to Active Support.
        self.env.board.spaces[5].pieces[5] = 1
        self.env.board.spaces[5].alignment = 0
        
        self.set_card(28)
        self.env.step(self.env._event_side_base + 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        
        self.env.step(self.env._target_space_action_base + 5)
        self.assertEqual(self.env.board.spaces[5].alignment, 1)
        self.assertTrue(self.env.board.spaces[5].support_active)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_carlos_prio_un_resources(self):
        # Card 33 (Carlos Prío, Un): +5 DR or +5 M26 Resources.
        self.env.players[2].resources = 10
        self.set_card(33)
        self.env.step(self.env._event_side_base + 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        
        self.env.step(self.env._target_faction_action_base + 2) # DR
        self.assertEqual(self.env.players[2].resources, 15)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    @unittest.skip("Covered by tests/cubalibre/test_card_30_the_guerrilla_life.py")
    def test_guerrilla_life_sh_place(self):
        # Card 30 (The Guerrilla Life, Sh): Flip DR underground, place 1 DR in City.
        self.env.board.spaces[0].pieces[6] = 2 # 2 Active DR in Pinar
        self.set_card(30)
        
        self.env.step(self.env._event_side_base + 1) # Shaded
        assert self.env.board.spaces[0].pieces[5] == 2 # Flipped
        assert self.env.board.spaces[0].pieces[6] == 0
        assert self.env.phase == PHASE_CHOOSE_TARGET_SPACE
        
        # Place in Havana (3)
        self.env.step(self.env._target_space_action_base + 3)
        assert self.env.board.spaces[3].pieces[5] >= 1
        assert self.env.phase == PHASE_CHOOSE_MAIN

    @unittest.skip("Covered by tests/cubalibre/test_card_30_the_guerrilla_life.py")
    def test_guerrilla_life_sh_no_available_guerrillas(self):
        # Card 30 (The Guerrilla Life, Sh): If no DR Guerrillas are available, do not allow placement.
        self.env.players[2].available_forces[0] = 0
        self.env.board.spaces[3].pieces[5] = 0

        self.set_card(30)
        self.env.step(self.env._event_side_base + 1) # Shaded
        assert self.env.phase == PHASE_CHOOSE_TARGET_SPACE

        # No city should be a legal target.
        pick = self.env._target_space_action_base + 3
        assert self.env.legal_actions[pick] == 0
        assert self.env.players[2].available_forces[0] == 0

    def test_carlos_prio_sh_place_base(self):
        # Card 33 (Carlos Prío, Sh): Place DR Base in space without Govt Control.
        self.env.players[2].available_bases = 1
        # Santiago (12) has no Govt
        self.env.board.spaces[12].pieces[0] = 0
        self.env.board.spaces[12].pieces[1] = 0
        self.env.board.spaces[12].govt_bases = 0
        self.env.board.spaces[12].update_control()
        
        self.set_card(33)
        self.env.step(self.env._event_side_base + 1) # Shaded
        assert self.env.phase == PHASE_CHOOSE_TARGET_SPACE
        
        self.env.step(self.env._target_space_action_base + 12)
        assert self.env.board.spaces[12].pieces[7] == 1 # DR Base
        assert self.env.board.spaces[12].alignment == 0 # Neutral
        assert self.env.phase == PHASE_CHOOSE_MAIN

    def test_carlos_prio_sh_no_available_bases_does_not_place(self):
        # Card 33 (Carlos Prío, Sh): If no DR bases are available, do not place (and do not go negative).
        self.env.players[2].available_bases = 0
        self.env.board.spaces[12].pieces[7] = 0
        self.env.board.spaces[12].pieces[0] = 0
        self.env.board.spaces[12].pieces[1] = 0
        self.env.board.spaces[12].govt_bases = 0
        self.env.board.spaces[12].update_control()

        self.set_card(33)
        self.env.step(self.env._event_side_base + 1)  # Shaded

        # No legal target spaces should be available when no bases.
        pick = self.env._target_space_action_base + 12
        assert self.env.legal_actions[pick] == 0
        assert self.env.players[2].available_bases == 0

    def test_speaking_tour_un_resources(self):
        # Card 34 (US Speaking Tour, Un): +Roll for 1, +2 for other.
        self.env.players[1].resources = 10
        self.env.players[2].resources = 10
        self.set_card(34)
        
        self.env.step(self.env._event_side_base + 0) # Unshaded
        assert self.env.phase == PHASE_CHOOSE_TARGET_FACTION
        
        # Choose M26 (1)
        self.env.step(self.env._target_faction_action_base + 1)
        assert self.env.players[1].resources > 10
        assert self.env.players[2].resources == 12
        assert self.env.phase == PHASE_CHOOSE_MAIN

if __name__ == '__main__':
    unittest.main()
