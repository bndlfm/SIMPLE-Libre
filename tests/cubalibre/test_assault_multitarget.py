import unittest
import numpy as np
from app.environments.cubalibre.envs.env import CubaLibreEnv, OP_ASSAULT, PHASE_CHOOSE_OP_ACTION, PHASE_CHOOSE_TARGET_FACTION, PHASE_CHOOSE_SPECIAL_ACTIVITY

class TestAssaultMultiTarget(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=True)
        self.env.reset()

    def test_assault_multitarget_pause(self):
        # Setup Havana (Space 0) with multiple insurgents
        havana = self.env.board.spaces[0]
        havana.type = 0 # Force City for Full Assault
        # Govt needs Troops to Assault
        havana.pieces[0] = 5 # Troops
        havana.pieces[1] = 5 # Police
        
        # Add M26
        havana.pieces[2] = 1 # M26 UG
        havana.pieces[3] = 1 # M26 Active
        
        # Add DR
        havana.pieces[5] = 1 # DR UG
        havana.pieces[6] = 1 # DR Active

        # Set Govt as current player and give resources
        self.env.current_player_num = 0
        self.env.players[0].resources = 20
        self.env.players[0].eligible = True
        
        # Force Phase to Choose Op Action
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env._ops_action_base = 0 # Assume base is 0 for simplicity or fetch from env
        
        # Calculate Action ID for Assault Havana
        # Op Action = OpsBase + (Op_ID * NumSpaces) + SpaceID
        assault_op_id = OP_ASSAULT
        action_id = self.env._ops_action_base + (assault_op_id * self.env.num_spaces) + 0
        
        print(f"Executing Assault on Havana (Action {action_id})")
        
        # Step
        obs, reward, done, truncated, info = self.env.step(action_id)
        
        # Verify Pause
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION, "Should pause for faction selection")
        self.assertIsNotNone(self.env._pending_event_faction, "Should have pending faction selection state")
        self.assertEqual(self.env._pending_event_faction["event"], "OP_ASSAULT")
        self.assertEqual(len(self.env._pending_event_faction["allowed"]), 2, "Should allow M26 and DR")
        
        # Verify Context
        self.assertEqual(self.env._pending_event_faction.get("context"), "OP")
        
        # Select M26 (Idx 1)
        # Target Faction Action Base
        target_action_base = self.env._target_faction_action_base
        m26_action = target_action_base + 1
        
        print(f"Selecting M26 (Action {m26_action})")
        obs, reward, done, truncated, info = self.env.step(m26_action)
        
        # Verify Execution
        # M26 Active should be removed first (Active > Base > UG)
        # We had 1 Active, 1 UG. 
        # Killers = 5 Troops + 5 Police.
        # Troops kill Active. Police kill UG.
        # Result: 0 Active, 0 UG.
        self.assertEqual(havana.pieces[3], 0, "M26 Active should be removed")
        self.assertEqual(havana.pieces[2], 0, "M26 UG should be removed")
        
        # DR should be untouched
        self.assertEqual(havana.pieces[6], 1, "DR Active should be untouched")
        self.assertEqual(havana.pieces[5], 1, "DR UG should be untouched")
        
        # Verify Resume to SA Phase
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY, "Should resume to SA phase")
        self.assertTrue(self.env._pending_sa, "Pending SA should be true")

if __name__ == '__main__':
    unittest.main()
