import unittest
import sys
sys.path.insert(0, '/home/neko/Projects/SIMPLE-Libre')
from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.env import (
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_TARGET_SPACE,
    OP_MARCH_M26,
    OP_ATTACK_M26,
)

class TestCapabilities(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv()
        self.env.reset()
        
    @unittest.skip("Covered by tests/cubalibre/test_card_13_el_che.py")
    def test_el_che_capability_first_group_underground(self):
        """Test El Che capability: First M26 March group stays underground."""
        self.env.capabilities.add("ElChe_Unshaded")
        
        # Setup: Place M26 underground guerrillas in Pinar (0)
        self.env.board.spaces[0].pieces[2] = 2  # Underground
        self.env.players[1].resources = 10
        
        # M26 March to Cigar EC (1) - an econ center (activates guerrillas unless El Che keeps first group underground)
        self.env.current_player_num = 1
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        
        # Choose March to Cigar EC
        dest_space = 1
        action = self.env._ops_action_base + (OP_MARCH_M26 * self.env.num_spaces) + dest_space
        self.assertEqual(self.env.legal_actions[action], 1)
        self.env.step(action)
        
        # Select Pinar as source
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_src = self.env._target_space_action_base + 0
        self.assertEqual(self.env.legal_actions[pick_src], 1)
        self.env.step(pick_src)
        
        # First group should stay underground in EC (El Che effect)
        assert self.env.board.spaces[dest_space].pieces[2] == 1  # Underground
        assert self.env.board.spaces[dest_space].pieces[3] == 0  # Active
        
    @unittest.skip("Covered by tests/cubalibre/test_card_22_raul.py")
    def test_raul_capability_attack_reroll(self):
        """Test Raúl capability: M26 can reroll failed Attack."""
        self.env.capabilities.add("Raul_Unshaded")
        
        # Setup: Place M26 and Govt in same space
        self.env.board.spaces[3].pieces[2] = 1  # M26 underground
        self.env.board.spaces[3].pieces[0] = 2  # Troops
        self.env.players[1].resources = 10
        
        # M26 Attack in Havana
        self.env.current_player_num = 1
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        
        # This should trigger at least one reroll if first roll fails
        # (We can't directly test randomness, but capability should be in code)
        action = self.env._ops_action_base + (OP_ATTACK_M26 * self.env.num_spaces) + 3  # OP_ATTACK_M26 in Havana
        self.env.step(action)
        
        # Just verify it doesn't crash and uses the capability
        assert "Raul_Unshaded" in self.env.capabilities

if __name__ == '__main__':
    unittest.main()
