import unittest
from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_TARGET_SPACE,
)

@unittest.skip("Covered by tests/cubalibre/test_card_12_brac.py")
class TestBracUnshadedTargetSelection(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.update_control()

    def test_brac_unshaded_removes_two_guerrillas_agent_driven(self):
        # Card 12: BRAC
        d = EVENT_DECK_DATA[12]
        self.env.current_card = Card(12, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0 # GOVT
        self.env.players[0].eligible = True
        self.env.phase = 0
        
        # Place 1 M26 in Santiago, 1 DR in Havana, 1 Syn in Camaguey
        self.env.board.spaces[12].pieces[2] = 1 # M26
        self.env.board.spaces[1].pieces[5] = 1 # DR
        self.env.board.spaces[8].pieces[8] = 1 # Syn
        
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Should be in target choice phase
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_event_target["count"], 0)
        
        # Pick Santiago
        self.env.step(self.env._target_space_action_base + 12)
        
        # Effect: M26 in Santiago removed. Should STILL be in target choice phase for the 2nd one.
        self.assertEqual(int(self.env.board.spaces[12].pieces[2]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_event_target["count"], 1)
        
        # Pick Havana
        self.env.step(self.env._target_space_action_base + 1)
        
        # Effect: DR in Havana removed. Should now finish and return to MAIN phase.
        self.assertEqual(int(self.env.board.spaces[1].pieces[5]), 0)
        self.assertEqual(self.env.phase, 0) # PHASE_CHOOSE_MAIN
        
        # Syn in Camaguey should still be there
        self.assertEqual(int(self.env.board.spaces[8].pieces[8]), 1)

if __name__ == "__main__":
    unittest.main()
