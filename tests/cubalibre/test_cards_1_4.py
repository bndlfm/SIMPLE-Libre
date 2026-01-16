import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.env import (
    MAIN_OPS,
    MAIN_PASS,
    OP_ASSAULT,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_TARGET_SPACE,
)
from app.environments.cubalibre.envs.events import resolve_event


class TestCards1To4(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=1)

        self.env.current_player_num = 0

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False

        self.env.capabilities.clear()

    def test_card_1_armored_cars_unshaded_march_and_ambush(self):
        self.env.current_card = Card(1, "Armored Cars", [0, 1, 2, 3], "", "")

        # Force M26 as executing faction for determinism.
        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        # Destination (0) has Govt pieces; Source (1) has multiple M26 guerrillas.
        # Destination does NOT need to satisfy any extra restrictions beyond being a valid space.
        self.env.board.spaces[0].pieces[0] = 2  # Troops
        self.env.board.spaces[0].pieces[1] = 1  # Police
        self.env.board.spaces[1].pieces[2] = 2  # M26 underground
        self.env.board.spaces[1].pieces[3] = 1  # M26 active

        # Ensure adjacency between 0 and 1 (both directions).
        if 1 not in self.env.board.spaces[0].adj_ids:
            self.env.board.spaces[0].adj_ids = list(set(self.env.board.spaces[0].adj_ids + [1]))
        if 0 not in self.env.board.spaces[1].adj_ids:
            self.env.board.spaces[1].adj_ids = list(set(self.env.board.spaces[1].adj_ids + [0]))

        self.env.step(self.env._main_action_base + 1)  # MAIN_EVENT
        self.env.step(self.env._event_side_base + 0)   # EVENT_UNSHADED

        # Faction selection (M26 = 1)
        self.assertEqual(self.env.phase, 6) # PHASE_CHOOSE_TARGET_FACTION
        self.env.step(self.env._target_faction_action_base + 1)

        pick_target = self.env._target_space_action_base + 0
        self.assertEqual(self.env.legal_actions[pick_target], 1)
        self.env.step(pick_target)

        pick_src = self.env._target_space_action_base + 1
        self.assertEqual(self.env.legal_actions[pick_src], 1)
        self.env.step(pick_src)

        # All guerrillas in source should have marched.
        self.assertEqual(self.env.board.spaces[1].pieces[2] + self.env.board.spaces[1].pieces[3], 0)
        self.assertEqual(self.env.board.spaces[0].pieces[2] + self.env.board.spaces[0].pieces[3], 3)

        # Ambush kills up to 2 Govt pieces (Police first, then Troops).
        self.assertEqual(self.env.board.spaces[0].pieces[0] + self.env.board.spaces[0].pieces[1], 1)

    def test_card_1_armored_cars_shaded_adds_capability(self):
        self.env.current_card = Card(1, "Armored Cars", [0, 1, 2, 3], "", "")
        resolve_event(self.env, 1, play_shaded=True)
        self.assertIn("ArmoredCars_Shaded", self.env.capabilities)

    def test_card_1_armored_cars_shaded_reinforce_before_assault(self):
        # Armored Cars (Shaded): before Assault, move Troops from other spaces into Assault space.
        self.env.capabilities.add("ArmoredCars_Shaded")

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        dest = 0
        src = 1

        # Assault destination has Govt presence (Police) + an Active guerrilla.
        # Without reinforcing Troops, Assault would not kill an Active guerrilla (Police only hit Underground).
        self.env.board.spaces[dest].pieces[1] = 1
        self.env.board.spaces[dest].pieces[3] = 1
        self.env.board.spaces[dest].update_control()

        # Troops in a different space (does not need to be adjacent for the shaded capability).
        self.env.board.spaces[src].pieces[0] = 2
        self.env.board.spaces[src].update_control()

        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        assault_action = self.env._ops_action_base + (OP_ASSAULT * self.env.num_spaces + dest)
        self.env.step(assault_action)

        # ArmoredCars_Shaded should force a reinforcement selection phase.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # Move 1 Troop from src into dest.
        pick_src = self.env._target_space_action_base + src
        self.assertEqual(int(self.env.legal_actions[pick_src]), 1)
        self.env.step(pick_src)
        self.assertEqual(int(self.env.board.spaces[src].pieces[0]), 1)
        self.assertEqual(int(self.env.board.spaces[dest].pieces[0]), 1)

        # PASS ends reinforcement and resolves Assault.
        self.env.step(self.env._main_action_base + MAIN_PASS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)

        # Active guerrilla should be killed by the reinforced Troop.
        self.assertEqual(int(self.env.board.spaces[dest].pieces[3]), 0)

    @unittest.skip("Covered by tests/cubalibre/test_card_2_guantanamo_bay.py")
    def test_card_2_guantanamo_unshaded_capability(self):
        self.env.current_card = Card(2, "Guantanamo Bay", [0, 1, 2, 3], "", "")
        resolve_event(self.env, 2, play_shaded=False)
        self.assertIn("Guantanamo_Unshaded", self.env.capabilities)

    @unittest.skip("Covered by tests/cubalibre/test_card_2_guantanamo_bay.py")
    def test_card_2_guantanamo_shaded_capability(self):
        self.env.current_card = Card(2, "Guantanamo Bay", [0, 1, 2, 3], "", "")
        resolve_event(self.env, 2, play_shaded=True)
        self.assertIn("Guantanamo_Shaded", self.env.capabilities)

    def test_card_4_sim_shaded_clears_on_propaganda(self):
        self.env.current_card = Card(4, "S.I.M.", [0, 1, 2, 3], "", "")
        resolve_event(self.env, 4, play_shaded=True)
        self.assertIn("SIM_Shaded", self.env.capabilities)

        self.env.resolve_propaganda()
        self.assertNotIn("SIM_Shaded", self.env.capabilities)

    def test_propaganda_clears_other_expiring_capabilities(self):
        self.env.capabilities.add("Masferrer_Shaded")
        self.env.capabilities.add("Mosquera_Shaded")
        self.env.capabilities.add("MAP_Shaded")
        self.env.capabilities.add("ArmoredCars_Shaded")
        self.env.capabilities.add("Guantanamo_Shaded")

        self.env.resolve_propaganda()

        self.assertNotIn("Masferrer_Shaded", self.env.capabilities)
        self.assertNotIn("Mosquera_Shaded", self.env.capabilities)
        self.assertNotIn("MAP_Shaded", self.env.capabilities)
        self.assertNotIn("ArmoredCars_Shaded", self.env.capabilities)
        self.assertNotIn("Guantanamo_Shaded", self.env.capabilities)


if __name__ == "__main__":
    unittest.main()
