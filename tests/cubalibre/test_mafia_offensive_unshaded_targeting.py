import unittest
from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
)

class TestMafiaOffensiveUnshadedTargeting(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.update_control()

    def test_mafia_offensive_unshaded_choose_faction_enters_limited_ops(self):
        # Card 43: Mafia Offensive
        d = EVENT_DECK_DATA[43]
        self.env.current_card = Card(43, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 3 # SYNDICATE
        self.env.players[3].eligible = True
        self.env.phase = 0
        
        # Scenario: Place 6 M26 in Santiago with Govt Troops (valid for Attack heuristic, guaranteed success)
        # Place 6 DR in Havana with Govt Troops
        self.env.board.spaces[12].pieces[2] = 6 # M26
        self.env.board.spaces[12].pieces[0] = 1 # Troops
        self.env.board.spaces[1].pieces[5] = 6 # DR
        self.env.board.spaces[1].pieces[0] = 1 # Troops
        
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Should be in faction choice phase
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        
        # Choose M26 (index 1)
        self.env.step(self.env._target_faction_action_base + 1)
        
        # Effect: enter Limited Ops selection for the chosen faction.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_LIMITED_OP_ACTION)
        self.assertEqual(self.env._pending_mafia_offensive.get("faction"), 1)
        # No automatic attack should have happened yet.
        self.assertEqual(int(self.env.board.spaces[12].pieces[3]), 0)
        self.assertEqual(int(self.env.board.spaces[1].pieces[5]), 6)

if __name__ == "__main__":
    unittest.main()
