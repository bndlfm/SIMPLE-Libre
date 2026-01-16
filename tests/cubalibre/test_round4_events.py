import unittest
import numpy as np
from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.env import (
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_MAIN
)
from app.environments.cubalibre.envs.constants import *

class TestRound4Events(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv()
        self.env.reset()
        self.env._pending_propaganda = None
        self.env._propaganda_in_progress = False
        self.env._propaganda_final_round = False

    def set_card(self, card_id):
        matches = [c for c in self.env.deck.cards if c.id == card_id]
        if matches:
            self.env.current_card = matches[0]
            return
        data = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(
            card_id,
            data["name"],
            data["order"],
            data["unshaded"],
            data["shaded"],
        )

    @unittest.skip("Covered by tests/cubalibre/test_card_21_fangio.py")
    def test_fangio_un_shift_city(self):
        # Card 21 (Fangio, Un): City shift toward Active Opp. 2 levels if M26 piece.
        self.env.board.spaces[12].pieces[2] = 1 # M26 piece
        self.env.board.spaces[12].alignment = 1 # Support
        self.env.board.spaces[12].support_active = True
        self.set_card(21)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        self.env.step(self.env._target_space_action_base + 12)
        self.assertEqual(self.env.board.spaces[12].alignment, 0)

    @unittest.skip("Covered by tests/cubalibre/test_card_23_radio_rebelde.py")
    def test_radio_rebelde_sh_remove_base(self):
        # Card 23 (Radio Rebelde, Sh): Remove M26 Base from Province.
        self.env.board.spaces[0].pieces[4] = 1 # M26 Base
        self.set_card(23)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 1) # Shaded
        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(self.env.board.spaces[0].pieces[4], 0)

    @unittest.skip("Covered by tests/cubalibre/test_card_24_vilma_espin.py")
    def test_vilma_espin_un_set_opp(self):
        # Card 24 (Vilma Espín, Un): Set Sierra Maestra or adj to Active Opp.
        self.env.board.spaces[11].alignment = 1 # Sierra Maestra Support
        self.set_card(24)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        self.env.step(self.env._target_space_action_base + 11)
        self.assertEqual(self.env.board.spaces[11].alignment, 2)
        self.assertTrue(self.env.board.spaces[11].support_active)

    @unittest.skip("Covered by tests/cubalibre/test_card_25_escapade.py")
    def test_escapade_un_place(self):
        # Card 25 (Escapade, Un): Place DR Base and G in Camaguey (7) or Oriente (9).
        self.env.players[2].available_bases = 1
        self.env.players[2].available_forces[0] = 5
        self.set_card(25)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        self.env.step(self.env._target_space_action_base + 9) # Oriente
        self.assertEqual(self.env.board.spaces[9].pieces[7], 1) # Base
        self.assertEqual(self.env.board.spaces[9].pieces[5], 1) # G

    @unittest.skip("Covered by tests/cubalibre/test_card_25_escapade.py")
    def test_escapade_sh_remove_base(self):
        # Card 25 (Escapade, Sh): Remove DR Base.
        self.env.board.spaces[0].pieces[7] = 1 # DR Base
        self.set_card(25)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 1) # Shaded
        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(self.env.board.spaces[0].pieces[7], 0)

    @unittest.skip("Covered by tests/cubalibre/test_card_26_rodriguez_loeches.py")
    def test_loeches_sh_remove_res(self):
        # Card 26 (Rodríguez Loeches, Sh): Remove 1 DR G, DR Res -5.
        self.env.board.spaces[0].pieces[5] = 1
        self.env.players[2].resources = 10
        self.set_card(26)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 1) # Shaded
        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(self.env.board.spaces[0].pieces[5], 0)
        self.assertEqual(self.env.players[2].resources, 5)

    @unittest.skip("Covered by tests/cubalibre/test_card_27_echeverria.py")
    def test_echeverria_sh_remove_two(self):
        # Card 27 (Echeverría, Sh): Remove 2 DR pieces.
        self.env.board.spaces[0].pieces[5] = 1
        self.env.board.spaces[1].pieces[5] = 1
        self.set_card(27)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 1) # Shaded
        self.env.step(self.env._target_space_action_base + 0)
        self.env.step(self.env._target_space_action_base + 1)
        self.assertEqual(self.env.board.spaces[0].pieces[5], 0)
        self.assertEqual(self.env.board.spaces[1].pieces[5], 0)

    def test_escopeteros_un_faction_mountain(self):
        # Card 31 (Escopeteros, Un): Place any non-Casino Base and any 1 G into a Mountain.
        self.env.players[2].available_bases = 1
        self.env.players[2].available_forces[0] = 5
        self.set_card(31)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        self.env.step(self.env._target_space_action_base + 11) # Sierra Maestra
        self.env.step(self.env._target_faction_action_base + 2) # DR Base
        self.env.step(self.env._target_faction_action_base + 2) # DR Guerrilla
        self.assertEqual(self.env.board.spaces[11].pieces[7], 1)
        self.assertEqual(self.env.board.spaces[11].pieces[5], 1)

    def test_escopeteros_sh_shift_mountain(self):
        # Card 31 (Escopeteros, Sh): Shift Mountain toward Support.
        self.env.board.spaces[11].alignment = 2 # Opp
        self.env.board.spaces[11].support_active = False # Passive Opp
        self.set_card(31)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 1) # Shaded
        self.env.step(self.env._target_space_action_base + 11)
        self.assertEqual(self.env.board.spaces[11].alignment, 0) # Neutral

    def test_resistencia_un_replace(self):
        # Card 32 (Resistencia Cívica, Un): Replace DR with M26 in City.
        self.env.board.spaces[12].pieces[5] = 1  # 1 DR Underground
        self.env.board.spaces[12].pieces[6] = 1  # 1 DR Active
        self.env.players[1].available_forces[0] = 10
        self.set_card(32)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        self.env.step(self.env._target_space_action_base + 12)
        self.assertEqual(self.env.board.spaces[12].pieces[5], 0)
        self.assertEqual(self.env.board.spaces[12].pieces[6], 0)
        self.assertEqual(self.env.board.spaces[12].pieces[2], 1)
        self.assertEqual(self.env.board.spaces[12].pieces[3], 1)

    def test_resistencia_sh_replace(self):
        # Card 32 (Resistencia Cívica, Sh): Replace M26 with DR in City.
        self.env.board.spaces[12].pieces[2] = 2 # 2 M26 Underground
        self.env.players[2].available_forces[0] = 10
        self.set_card(32)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 1) # Shaded
        self.env.step(self.env._target_space_action_base + 12)
        self.assertEqual(self.env.board.spaces[12].pieces[2], 0)
        self.assertEqual(self.env.board.spaces[12].pieces[5], 2)

    def test_defections_un_replace(self):
        # Card 35 (Defections, Un): Replace 2 enemy pieces with current player pieces.
        # Current player is M26 (1)
        self.env.current_player_num = 1
        self.env.board.spaces[0].pieces[0] = 2 # 2 Govt Troops
        self.env.board.spaces[0].pieces[2] = 1 # Already has 1 M26
        self.env.players[1].available_forces[0] = 10
        self.set_card(35)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(self.env.board.spaces[0].pieces[0], 0)
        self.assertEqual(self.env.board.spaces[0].pieces[2], 3) # 1 original + 2 replaced

    def test_menoyo_un_replace(self):
        # Card 36 (Eloy Gutiérrez Menoyo, Un): Replace a non-DR non-Casino piece near Las Villas (5) with 2 DR G.
        self.env.board.spaces[5].pieces[0] = 1 # Govt Troop
        self.env.board.spaces[5].pieces[1] = 1 # Govt Police
        self.env.players[2].available_forces[0] = 10
        self.set_card(36)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        self.env.step(self.env._target_space_action_base + 5)
        if self.env.phase == PHASE_CHOOSE_EVENT_OPTION:
            self.env.step(self.env._event_option_action_base + 0)
        self.assertEqual(self.env.board.spaces[5].pieces[0], 0)
        self.assertEqual(self.env.board.spaces[5].pieces[5], 2)

    def test_menoyo_sh_replace(self):
        # Card 36 (Eloy Gutiérrez Menoyo, Sh): Replace a DR G with a non-DR G (M26).
        self.env.board.spaces[0].pieces[5] = 1 # DR G
        self.env.board.spaces[0].pieces[6] = 1 # DR Active
        self.env.players[1].available_forces[0] = 10
        self.set_card(36)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 1) # Shaded
        self.env.step(self.env._target_space_action_base + 0)
        if self.env.phase == PHASE_CHOOSE_EVENT_OPTION:
            self.env.step(self.env._event_option_action_base + 0)
        if self.env.phase == PHASE_CHOOSE_TARGET_FACTION:
            self.env.step(self.env._target_faction_action_base + 1)
        self.assertEqual(self.env.board.spaces[0].pieces[5], 0)
        self.assertEqual(self.env.board.spaces[0].pieces[2], 1) # M26

    def test_miami_sh_resources(self):
        # Card 47 (Pact of Miami, Sh): M26 and DR each lose 3 Res. Both Ineligible.
        self.env.players[1].resources = 10
        self.env.players[2].resources = 10
        self.env.players[1].eligible = True
        self.env.players[2].eligible = True
        self.set_card(47)
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 1) # Shaded
        self.assertEqual(self.env.players[1].resources, 7)
        self.assertEqual(self.env.players[2].resources, 7)
        self.assertFalse(self.env.players[1].eligible)
        self.assertFalse(self.env.players[2].eligible)

if __name__ == '__main__':
    unittest.main()
