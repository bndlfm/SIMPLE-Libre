import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_TARGET_SPACE,
    OP_TRANSPORT,
)


class TestOpsTransportTargetSelection(unittest.TestCase):
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

    def test_transport_requires_source_selection_then_moves_troops(self):
        # Use any non-propaganda card.
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        src = 0
        dest = 3
        self.env.board.spaces[src].pieces[0] = 4

        transport_to_dest = self.env._ops_action_base + OP_TRANSPORT * self.env.num_spaces + dest
        self.assertEqual(self.env.legal_actions[transport_to_dest], 1)

        self.env.step(transport_to_dest)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_src = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[pick_src], 1)

        before_src = int(self.env.board.spaces[src].pieces[0])
        before_dest = int(self.env.board.spaces[dest].pieces[0])

        self.env.step(pick_src)

        after_src = int(self.env.board.spaces[src].pieces[0])
        after_dest = int(self.env.board.spaces[dest].pieces[0])

        # Should move up to 3 troops.
        self.assertEqual(before_src - 3, after_src)
        self.assertEqual(before_dest + 3, after_dest)


if __name__ == "__main__":
    unittest.main()
