import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, MAIN_EVENT, EVENT_UNSHADED, PHASE_CHOOSE_TARGET_SPACE


class TestArmoredCarsUnshaded(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        # Clear board for deterministic setup
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

    def test_dr_free_march_then_free_ambush(self):
        d = EVENT_DECK_DATA[1]
        self.env.current_card = Card(1, d["name"], d["order"], d["unshaded"], d["shaded"])

        # Force DR as executing faction for heuristic
        self.env.current_player_num = 2
        self.env.players[2].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        # Set up: Govt pieces in Havana, DR guerrilla adjacent (La Habana)
        havana = 3
        adj = self.env.board.spaces[havana].adj_ids[0]
        # DR underground guerrilla adjacent
        self.env.board.spaces[adj].pieces[5] = 1
        # Govt pieces in target
        self.env.board.spaces[havana].pieces[0] = 2
        self.env.board.spaces[havana].pieces[1] = 1

        before_adj = int(self.env.board.spaces[adj].pieces[5] + self.env.board.spaces[adj].pieces[6])
        before_target_dr = int(self.env.board.spaces[havana].pieces[5] + self.env.board.spaces[havana].pieces[6])
        before_govt = int(self.env.board.spaces[havana].pieces[0] + self.env.board.spaces[havana].pieces[1] + self.env.board.spaces[havana].govt_bases)

        # Play event unshaded
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Faction selection (DR = 2)
        self.assertEqual(self.env.phase, 6) # PHASE_CHOOSE_TARGET_FACTION
        self.env.step(self.env._target_faction_action_base + 2)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_target = self.env._target_space_action_base + havana
        self.assertEqual(self.env.legal_actions[pick_target], 1)
        self.env.step(pick_target)

        # Second step: choose the adjacent source space.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_src = self.env._target_space_action_base + adj
        self.assertEqual(self.env.legal_actions[pick_src], 1)
        self.env.step(pick_src)

        after_adj = int(self.env.board.spaces[adj].pieces[5] + self.env.board.spaces[adj].pieces[6])
        after_target_dr = int(self.env.board.spaces[havana].pieces[5] + self.env.board.spaces[havana].pieces[6])
        after_govt = int(self.env.board.spaces[havana].pieces[0] + self.env.board.spaces[havana].pieces[1] + self.env.board.spaces[havana].govt_bases)

        # March should have moved 1 DR guerrilla into the target
        self.assertEqual(before_adj - 1, after_adj)
        self.assertEqual(before_target_dr + 1, after_target_dr)

        # Ambush should remove up to 2 govt pieces
        self.assertLess(after_govt, before_govt)
        self.assertGreaterEqual(before_govt - after_govt, 1)
        self.assertLessEqual(before_govt - after_govt, 2)


if __name__ == "__main__":
    unittest.main()
