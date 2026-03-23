import unittest
import numpy as np
from app.environments.cubalibre.envs.env import CubaLibreEnv, OP_ATTACK_M26, PHASE_CHOOSE_OP_ACTION, PHASE_CHOOSE_EVENT_OPTION, PHASE_CHOOSE_SPECIAL_ACTIVITY

class TestAttackPieceSelection(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=True)
        self.env.reset()

    def test_attack_selection(self):
        # Setup Havana (Space 0 - forced to City in previous test, but here it's new env)
        # Space 1 is "Cigar EC", Space 3 is "Havana" (City).
        # Let's use Havana (Space 3).
        havana = self.env.board.spaces[3]
        
        # Setup Govt pieces
        havana.pieces[0] = 2 # Troops
        havana.pieces[1] = 2 # Police
        havana.govt_bases = 1 # Base
        
        # Setup M26 pieces (Ensure count >= 6 for guaranteed success)
        havana.pieces[2] = 4 # UG
        havana.pieces[3] = 4 # Active
        
        # Set M26 as current player
        self.env.current_player_num = 1
        self.env.players[1].resources = 10
        self.env.players[1].eligible = True
        
        # Force Phase
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        
        # Calculate Action ID for Attack Havana
        # Op Action = OpsBase + (Op_ID * NumSpaces) + SpaceID
        attack_op_id = OP_ATTACK_M26
        action_id = self.env._ops_action_base + (attack_op_id * self.env.num_spaces) + 3
        
        print(f"Executing Attack on Havana (Action {action_id})")
        
        # Step 1: Trigger Attack
        obs, reward, done, truncated, info = self.env.step(action_id)
        
        # Verify Pause for Selection 1
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION, "Should pause for piece selection (1st)")
        self.assertIsNotNone(self.env._pending_event_option, "Should have pending event option")
        self.assertEqual(self.env._pending_event_option["event"], "OP_ATTACK")
        self.assertEqual(self.env._pending_event_option["removals_left"], 2)
        # Allowed should include 0, 1, 2
        allowed = self.env._pending_event_option["allowed"]
        self.assertIn(0, allowed)
        self.assertIn(1, allowed)
        
        # Step 2: Select Troops (Option 0)
        # Event Option Action Base + Option
        option_action = self.env._event_option_action_base + 0
        print(f"Selecting Troops (Action {option_action})")
        
        obs, reward, done, truncated, info = self.env.step(option_action)
        
        # Verify Removal 1
        self.assertEqual(havana.pieces[0], 1, "Troops should decrease by 1")
        
        # Verify Pause for Selection 2
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION, "Should pause for piece selection (2nd)")
        self.assertEqual(self.env._pending_event_option["removals_left"], 1)
        
        # Step 3: Select Police (Option 1)
        option_action = self.env._event_option_action_base + 1
        print(f"Selecting Police (Action {option_action})")
        
        obs, reward, done, truncated, info = self.env.step(option_action)
        
        # Verify Removal 2
        self.assertEqual(havana.pieces[1], 1, "Police should decrease by 1")
        
        # Verify Resume to SA
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY, "Should resume to SA phase")

if __name__ == '__main__':
    unittest.main()
