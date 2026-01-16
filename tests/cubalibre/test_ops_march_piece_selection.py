import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_UNSHADED,
    MAIN_EVENT,
    OP_MARCH_M26,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestOpsMarchPieceSelection(unittest.TestCase):
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

    def test_march_prompts_piece_choice_when_active_and_underground_present(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 1  # M26
        self.env.players[1].eligible = True
        self.env.players[1].resources = 10
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        dest = next(sp.id for sp in self.env.board.spaces if sp.type in [1, 2, 3] and sp.adj_ids)
        src = self.env.board.spaces[dest].adj_ids[0]
        if src == dest:
            src = (dest + 1) % self.env.num_spaces
            self.env.board.spaces[dest].adj_ids = [src]

        self.env.board.spaces[src].pieces[2] = 1  # M26 Underground
        self.env.board.spaces[src].pieces[3] = 1  # M26 Active

        march_to_dest = self.env._ops_action_base + OP_MARCH_M26 * self.env.num_spaces + dest
        self.assertEqual(self.env.legal_actions[march_to_dest], 1)

        self.env.step(march_to_dest)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_src = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[pick_src], 1)
        self.env.step(pick_src)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        choose_active = self.env._event_option_action_base + 1
        self.assertEqual(self.env.legal_actions[choose_active], 1)

        before_src_active = int(self.env.board.spaces[src].pieces[3])
        before_dest_active = int(self.env.board.spaces[dest].pieces[3])

        self.env.step(choose_active)
        self.assertEqual(int(self.env.board.spaces[src].pieces[3]), before_src_active - 1)
        self.assertEqual(int(self.env.board.spaces[dest].pieces[3]), before_dest_active + 1)

        if self.env.phase == PHASE_CHOOSE_TARGET_SPACE:
            self.env.step(self.env._main_action_base + 0)


if __name__ == "__main__":
    unittest.main()
