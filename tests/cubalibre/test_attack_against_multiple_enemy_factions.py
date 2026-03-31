import unittest
import numpy as np

from app.environments.cubalibre.envs.env import CubaLibreEnv

class Test_test_attack_against_multiple_enemy_factions(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=True)
        self.env.reset(seed=42)

    def test_attack_against_multiple_enemy_factions(self):
        # Setup Havana (Space 3)
        sp = self.env.board.spaces[3]
        sp.pieces[:] = 0
        sp.govt_bases = 0

        # Add M26 pieces for attacking
        sp.pieces[2] = 4 # UG
        sp.pieces[3] = 4 # Active

        # Add Govt Police
        sp.pieces[1] = 1  # Police
        # Add DR Guerrillas
        sp.pieces[5] = 1 # DR UG
        sp.pieces[6] = 1 # DR Active

        self.env.current_player_num = 1 # M26

        # Trigger attack insurgent via step() to ensure phase transitions are handled correctly.
        # Op Action = OpsBase + (Op_ID * NumSpaces) + SpaceID
        # M26 Attack ID = 9. Havana ID = 3.
        action_id = self.env._ops_action_base + (9 * self.env.num_spaces) + 3

        # We need to be in the correct phase and resources
        self.env.phase = 2 # PHASE_CHOOSE_OP_ACTION
        self.env.players[1].resources = 10
        self.env.players[1].eligible = True

        self.env.step(action_id)

        self.assertEqual(self.env.phase, 6, "Should pause to choose faction")

        # Verify allowed factions are 0 (Govt) and 2 (DR)
        allowed = self.env._pending_event_faction["allowed"]
        self.assertIn(0, allowed)
        self.assertIn(2, allowed)
        self.assertNotIn(3, allowed)

        # Select DR (Faction 2)
        # Action = faction action base + 2
        faction_action = self.env._target_faction_action_base + 2
        obs, reward, done, truncated, info = self.env.step(faction_action)

        # Now it should pause for piece selection (Phase 7)
        self.assertEqual(self.env.phase, 7, "Should pause for piece type selection")
        self.assertEqual(self.env._pending_event_option["target_faction"], 2)

        # DR has UG (0) and Active (1) available
        allowed_pieces = self.env._pending_event_option["allowed"]
        self.assertIn(0, allowed_pieces)
        self.assertIn(1, allowed_pieces)

        # Select Active (1)
        # Action = option action base + 1
        piece_action = self.env._event_option_action_base + 1
        obs, reward, done, truncated, info = self.env.step(piece_action)

        self.assertEqual(int(sp.pieces[6]), 0, "DR Active should be killed")
        self.assertEqual(int(sp.pieces[5]), 1, "DR UG should survive")
        self.assertEqual(int(sp.pieces[1]), 1, "Govt Police should survive")



if __name__ == '__main__':
    unittest.main()
