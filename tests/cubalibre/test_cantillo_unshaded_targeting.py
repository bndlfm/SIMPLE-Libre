import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    MAIN_PASS,
    EVENT_UNSHADED,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
)


class TestCantilloUnshadedTargeting(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.closed_casinos = 0
            sp.cash[:] = 0
            sp.cash_holders[:] = 0
            sp.update_control()

    def test_cantillo_unshaded_three_step_flow(self):
        d = EVENT_DECK_DATA[3]
        self.env.current_card = Card(3, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        src = 2  # La Habana

        # Qualify source: Troops + Guerrillas (use M26 to keep assertions simple)
        self.env.board.spaces[src].pieces[0] = 1  # Troops
        self.env.board.spaces[src].pieces[2] = 1  # M26 Underground
        self.env.board.spaces[src].pieces[3] = 1  # M26 Active
        self.env.board.spaces[src].update_control()

        # Choose destinations dynamically from adjacency to avoid hardcoding map IDs.
        adj = list(self.env.board.spaces[src].adj_ids)
        self.assertTrue(len(adj) > 0)
        dest1 = adj[0]
        dest2 = adj[1] if len(adj) > 1 else dest1
        self.env.board.spaces[dest1].update_control()
        self.env.board.spaces[dest2].update_control()

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Step 1: choose the source space
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_src = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[pick_src], 1)
        self.env.step(pick_src)

        # Step 2: choose faction (M26)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        choose_m26 = self.env._target_faction_action_base + 1
        self.assertEqual(self.env.legal_actions[choose_m26], 1)
        self.env.step(choose_m26)

        # Step 3: choose destination space (adjacent)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_dest1 = self.env._target_space_action_base + dest1
        pick_dest2 = self.env._target_space_action_base + dest2
        self.assertEqual(self.env.legal_actions[pick_dest1], 1)

        before_dest1_u = int(self.env.board.spaces[dest1].pieces[2])
        before_dest2_u = int(self.env.board.spaces[dest2].pieces[2])
        # Free March out moves 1 guerrilla per destination pick.
        self.env.step(pick_dest1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env.legal_actions[pick_dest2], 1)
        self.env.step(pick_dest2)

        # PASS ends the event once all guerrillas have marched out.
        self.env.step(self.env._main_action_base + MAIN_PASS)
        after_dest1_u = int(self.env.board.spaces[dest1].pieces[2])
        after_dest2_u = int(self.env.board.spaces[dest2].pieces[2])

        # All M26 guerrillas from src moved to dest and are Underground
        self.assertEqual(int(self.env.board.spaces[src].pieces[2] + self.env.board.spaces[src].pieces[3]), 0)
        self.assertEqual((after_dest1_u + after_dest2_u), (before_dest1_u + before_dest2_u) + 2)


if __name__ == "__main__":
    unittest.main()
