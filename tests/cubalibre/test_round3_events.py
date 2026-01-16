import unittest
import numpy as np
from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.env import (
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_MAIN,
    MAIN_PASS
)
from app.environments.cubalibre.envs.constants import *

class TestRound3Events(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv()
        self.env.reset()
        self.env._pending_propaganda = None
        self.env._propaganda_in_progress = False
        self.env._propaganda_final_round = False
        # Ensure we have a valid card object to work with
        self.env.current_card = self.env.deck.cards[0]

    def test_armored_cars_un_faction_march_ambush(self):
        # Card 1 (Armored Cars, Un): 26July or DR free Marches into a space and free Ambushes there.
        # 1. Setup pieces: M26 pieces in Pinar del Rio (0), Govt pieces in La Habana (2).
        # Pinar del Rio (0) and La Habana (2) are adjacent.
        self.env.board.spaces[0].pieces[2] = 2 # M26 Underground
        self.env.board.spaces[2].pieces[1] = 2 # Police in La Habana
        self.env.board.spaces[0].update_control()
        self.env.board.spaces[2].update_control()
        
        # 2. Trigger event
        self.env.current_card.id = 1
        self.env.current_card.name = "Armored Cars"
        
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.env.step(self.env._target_faction_action_base + 1) # Select M26
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        # Stage TARGET: Select La Habana (2) as destination
        self.env.step(self.env._target_space_action_base + 2)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        # Stage SRC: Select Pinar Del Rio (0) as source
        self.env.step(self.env._target_space_action_base + 0)
        
        # Verify result
        # New behavior: free March moves all selected faction guerrillas from the chosen source.
        self.assertEqual(self.env.board.spaces[0].pieces[2], 0)
        self.assertEqual(self.env.board.spaces[2].pieces[2], 2) # Pieces moved
        self.assertEqual(self.env.board.spaces[2].pieces[1], 0) # Ambush killed both police
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_cantillo_un_multi_step(self):
        # Card 3 (Cantillo, Un)
        self.env.board.spaces[11].pieces[0] = 2 # Troops in Sierra Maestra
        self.env.board.spaces[11].pieces[6] = 2 # DR Active
        self.env.board.spaces[11].update_control()
        self.env.board.spaces[9].update_control()
        self.env.board.spaces[10].update_control()
        
        self.env.current_card.id = 3
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE) # Choose space with troops
        self.env.step(self.env._target_space_action_base + 11)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION) # Choose faction (DR=2)
        self.env.step(self.env._target_faction_action_base + 2)

        # Free March out: move guerrillas to adjacent destinations (can be multiple destinations).
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 9)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 10)

        # Source should now be empty of DR guerrillas.
        self.assertEqual(int(self.env.board.spaces[11].pieces[5] + self.env.board.spaces[11].pieces[6]), 0)
        # Both moved guerrillas should be Underground.
        self.assertEqual(int(self.env.board.spaces[9].pieces[5] + self.env.board.spaces[10].pieces[5]), 2)

        # PASS ends the event once all guerrillas have marched out.
        self.env.step(self.env._main_action_base + MAIN_PASS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    @unittest.skip("Covered by tests/cubalibre/test_card_11_batista_flees.py")
    def test_batista_flees_un_troop_removal(self):
        # Card 47 (Batista Flees, Un) - Note: In current env.py it's handled for card_id 11 but deck data might differ.
        self.env.current_card.id = 11 
        for i in range(5):
            self.env.board.spaces[i].pieces[0] = 5
        self.env.players[0].resources = 20
        
        original_roll = self.env._roll_die
        self.env._roll_die = lambda: 3
        
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0) # Unshaded
        
        self.assertEqual(self.env.players[0].resources, 10)
        
        for _ in range(3):
            self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
            target = -1
            for i in range(13):
                if self.env.board.spaces[i].pieces[0] > 0:
                    target = i
                    break
            before = self.env.board.spaces[target].pieces[0]
            self.env.step(self.env._target_space_action_base + target)
            self.assertEqual(self.env.board.spaces[target].pieces[0], before - 1)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.env._roll_die = original_roll

    @unittest.skip("Covered by tests/cubalibre/test_card_10_map.py")
    def test_map_un_replace(self):
        # Card 10 (MAP, Un)
        self.env.board.spaces[3].pieces[1] = 1 # Police in Havana (3)
        self.env.players[0].available_forces[1] = 0
        self.env.players[1].available_forces[0] = 10
        
        self.env.current_card.id = 10
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.step(self.env._event_side_base + 0)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 3)

        # Choose factions for the 2 guerrillas (pick M26 twice)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.env.step(self.env._target_faction_action_base + 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.env.step(self.env._target_faction_action_base + 1)
        
        self.assertEqual(self.env.board.spaces[3].pieces[1], 0)
        self.assertEqual(self.env.board.spaces[3].pieces[2], 2) # 2 M26 Underground
        self.assertEqual(self.env.players[0].available_forces[1], 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

if __name__ == '__main__':
    unittest.main()
