import random
import unittest

import numpy as np

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_PIECE,
)


class TestCashHolderTracking(unittest.TestCase):
    def setUp(self):
        self._random_state = random.getstate()
        self._np_random_state = np.random.get_state()
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash_holders[:] = 0
            sp.refresh_cash_counts()
            sp.update_control()

    def tearDown(self):
        random.setstate(self._random_state)
        np.random.set_state(self._np_random_state)

    def test_cash_moves_with_piece(self):
        src_id = 2
        dest_id = 3
        src = self.env.board.spaces[src_id]
        dest = self.env.board.spaces[dest_id]

        src.pieces[2] = 1  # M26 Underground
        self.assertTrue(self.env._add_cash_marker(src, 1, preferred_idx=2))

        self.env._move_pieces_with_cash(src_id, dest_id, 1, 0, 1)

        self.assertEqual(int(src.cash_holders[2]), 0)
        self.assertEqual(int(dest.cash_holders[2]), 1)
        self.assertEqual(int(dest.cash[1]), 1)

    def test_cash_transfer_when_holder_piece_removed(self):
        space_id = 3
        sp = self.env.board.spaces[space_id]
        sp.pieces[2] = 1  # M26 Underground
        self.assertTrue(self.env._add_cash_marker(sp, 1, preferred_idx=2))

        self.env.board.remove_piece(space_id, 1, 0)

        self.assertTrue(self.env._cash_transfer_waiting)
        self.env.phase = PHASE_CHOOSE_MAIN

        remove_cash_action = self.env._target_piece_action_base + (self.env._target_piece_action_count - 1)
        self.env.step(remove_cash_action)

        self.assertEqual(int(sp.cash_holders[2]), 0)
        self.assertFalse(self.env._cash_transfer_waiting)
        self.assertFalse(self.env._cash_transfer_active)

    def test_meyer_lansky_un_moves_cash_holder(self):
        d = EVENT_DECK_DATA[38]
        self.env.current_card = Card(38, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 3  # Syndicate
        self.env.players[3].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        space_id = 3
        sp = self.env.board.spaces[space_id]
        sp.pieces[2] = 1  # M26 Underground
        sp.pieces[5] = 1  # DR Underground
        self.assertTrue(self.env._add_cash_marker(sp, 1, preferred_idx=2))

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + space_id)

        # Holder-to-holder flow: select source holder then destination holder.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_PIECE)
        pick_src_holder = self.env._target_piece_action_base + 2
        self.assertEqual(int(self.env.legal_actions[pick_src_holder]), 1)
        self.env.step(pick_src_holder)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_PIECE)
        pick_dest_holder = self.env._target_piece_action_base + 5
        self.assertEqual(int(self.env.legal_actions[pick_dest_holder]), 1)
        self.env.step(pick_dest_holder)

        stop_action = self.env._target_piece_action_base + (self.env._target_piece_action_count - 1)
        self.assertEqual(int(self.env.legal_actions[stop_action]), 1)
        self.env.step(stop_action)

        self.assertEqual(int(sp.cash_holders[2]), 0)
        self.assertEqual(int(sp.cash_holders[5]), 1)


if __name__ == "__main__":
    unittest.main()
