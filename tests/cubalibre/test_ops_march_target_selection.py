import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_TARGET_SPACE,
    OP_MARCH_DR,
)


class TestOpsMarchTargetSelection(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

    def test_march_requires_source_selection_then_moves_guerrilla(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 2  # DR
        self.env.players[2].eligible = True
        self.env.players[2].resources = 10
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        dest = 3
        src = self.env.board.spaces[dest].adj_ids[0]
        if src == dest:
            src = (dest + 1) % self.env.num_spaces
            self.env.board.spaces[dest].adj_ids = [src]

        self.env.board.spaces[src].pieces[5] = 1

        march_to_dest = self.env._ops_action_base + OP_MARCH_DR * self.env.num_spaces + dest
        self.assertEqual(self.env.legal_actions[march_to_dest], 1)

        self.env.step(march_to_dest)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_src = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[pick_src], 1)

        before_src = int(self.env.board.spaces[src].pieces[5] + self.env.board.spaces[src].pieces[6])
        before_dest = int(self.env.board.spaces[dest].pieces[5] + self.env.board.spaces[dest].pieces[6])

        self.env.step(pick_src)

        after_src = int(self.env.board.spaces[src].pieces[5] + self.env.board.spaces[src].pieces[6])
        after_dest = int(self.env.board.spaces[dest].pieces[5] + self.env.board.spaces[dest].pieces[6])

        self.assertEqual(before_src - 1, after_src)
        self.assertEqual(before_dest + 1, after_dest)
        if self.env.phase == PHASE_CHOOSE_TARGET_SPACE:
            self.env.step(self.env._main_action_base + 0)


if __name__ == "__main__":
    unittest.main()
