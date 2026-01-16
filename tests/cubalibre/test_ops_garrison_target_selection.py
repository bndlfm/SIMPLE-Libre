import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    OP_GARRISON,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestOpsGarrisonTargetSelection(unittest.TestCase):
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

    def test_garrison_moves_selected_police_from_adjacent_source(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0  # GOVT
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        dest = 3
        src = self.env.board.spaces[dest].adj_ids[0]
        if src == dest:
            src = (dest + 1) % self.env.num_spaces
            self.env.board.spaces[dest].adj_ids = [src]

        self.env.board.spaces[src].pieces[1] = 2

        garrison = self.env._ops_action_base + OP_GARRISON * self.env.num_spaces + dest
        self.assertEqual(self.env.legal_actions[garrison], 1)

        self.env.step(garrison)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_src = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[pick_src], 1)
        self.env.step(pick_src)

        move_two = self.env._event_option_action_base + 1
        self.assertEqual(self.env.legal_actions[move_two], 1)
        self.env.step(move_two)

        self.assertEqual(self.env.board.spaces[src].pieces[1], 0)
        self.assertEqual(self.env.board.spaces[dest].pieces[1], 2)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)


if __name__ == "__main__":
    unittest.main()
