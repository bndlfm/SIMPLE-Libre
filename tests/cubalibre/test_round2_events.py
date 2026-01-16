import unittest
from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    EVENT_SHADED,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
)

class TestRound2Events(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.update_control()

    @unittest.skip("Covered by tests/cubalibre/test_card_15_come_comrades.py")
    def test_come_comrades_un_three_placements(self):
        # Card 15: Come Comrades! (Un): Place 3 M26 Guerrillas anywhere.
        d = EVENT_DECK_DATA[15]
        self.env.current_card = Card(15, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 1 # M26
        self.env.players[1].eligible = True
        
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        
        # 3 steps of placement
        for i, s_id in enumerate([0, 1, 2]):
            self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
            self.assertEqual(self.env._pending_event_target["count"], i)
            self.env.step(self.env._target_space_action_base + s_id)
            self.assertEqual(int(self.env.board.spaces[s_id].pieces[2]), 1)
        
        # Finished
        self.assertEqual(self.env.phase, 0) # PHASE_CHOOSE_MAIN

    @unittest.skip("Covered by tests/cubalibre/test_card_17_alberto_bayo.py")
    def test_alberto_bayo_un_faction_choice_rallies(self):
        # Card 17: Alberto Bayo (Un): 26July or DR free Rallies in each space it has a Base.
        d = EVENT_DECK_DATA[17]
        self.env.current_card = Card(17, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        
        # Place DR Bases in 2 spaces
        self.env.board.spaces[5].pieces[7] = 1 # DR Base in Escambray
        self.env.board.spaces[9].pieces[7] = 1 # DR Base in Oriente
        
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        # Choose DR (index 2)
        self.env.step(self.env._target_faction_action_base + 2)
        
        # Verify rallies: 1 DR guerrilla in Escambray & Oriente
        self.assertEqual(int(self.env.board.spaces[5].pieces[5]), 1)
        self.assertEqual(int(self.env.board.spaces[9].pieces[5]), 1)
        self.assertEqual(self.env.phase, 0)

    @unittest.skip("Covered by tests/cubalibre/test_card_20_the_twelve.py")
    def test_the_twelve_un_march_rally(self):
        # Card 20: The Twelve (Un): A Faction free Marches then free Rallies at a March destination.
        d = EVENT_DECK_DATA[20]
        self.env.current_card = Card(20, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        
        # M26 piece in Sierra Maestra (11), destination Oriente (9) - adjacent
        self.env.board.spaces[11].pieces[2] = 1 
        
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        # Choose M26 (index 1)
        self.env.step(self.env._target_faction_action_base + 1)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        # Choose Oriente (9) as destination
        self.env.step(self.env._target_space_action_base + 9)
        
        # Verify result: March (1 moved to 9) + Rally (1 placed in 9) = 2 in 9
        self.assertEqual(int(self.env.board.spaces[9].pieces[2]), 2)
        self.assertEqual(int(self.env.board.spaces[11].pieces[2]), 0)
        self.assertEqual(self.env.phase, 0)

    def test_carlos_prio_shaded_base_placement(self):
        # Card 33: Carlos Prío (Sh): Select a space without Govt Control. Place a DR Base. Set to Neutral.
        d = EVENT_DECK_DATA[33]
        self.env.current_card = Card(33, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 0 # GOVT
        self.env.players[0].eligible = True
        
        # Havana (1) controlled by Govt, Oriente (9) not.
        self.env.board.spaces[1].pieces[0] = 10 # Troops
        self.env.board.spaces[1].update_control()
        self.assertEqual(self.env.board.spaces[1].controlled_by, 1)
        
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)
        
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        # Havana should be illegal, Oriente legal
        self.assertEqual(self.env.legal_actions[self.env._target_space_action_base + 1], 0)
        self.assertEqual(self.env.legal_actions[self.env._target_space_action_base + 9], 1)
        
        # Place in Oriente
        self.env.step(self.env._target_space_action_base + 9)
        self.assertEqual(int(self.env.board.spaces[9].pieces[7]), 1) # DR Base
        self.assertEqual(int(self.env.board.spaces[9].alignment), 0)
        self.assertEqual(self.env.phase, 0)

if __name__ == "__main__":
    unittest.main()
