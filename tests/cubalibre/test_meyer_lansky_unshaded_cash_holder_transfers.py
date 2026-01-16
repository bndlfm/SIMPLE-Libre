import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_PIECE,
    PHASE_CHOOSE_MAIN,
)


class TestMeyerLanskyUnshadedCashHolderTransfers(unittest.TestCase):
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
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            sp.update_control()

    def test_meyer_lansky_unshaded_transfers_cash_between_holders_preserving_owner(self):
        d = EVENT_DECK_DATA[38]
        self.env.current_card = Card(38, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        s_id = 3  # Havana
        sp = self.env.board.spaces[s_id]

        # Create two Govt holders.
        sp.pieces[0] = 1  # Troop holder idx 0
        sp.pieces[1] = 1  # Police holder idx 1

        # Place 1 Syndicate-owned cash marker held by Police.
        sp.cash_holders[1] = 1
        sp.cash_owner_by_holder[1] = 3
        sp.refresh_cash_counts()

        self.assertEqual(int(sp.cash[3]), 1)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_space = self.env._target_space_action_base + s_id
        self.assertEqual(int(self.env.legal_actions[pick_space]), 1)
        self.env.step(pick_space)

        # Should now choose a source cash holder.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_PIECE)

        pick_src_holder = self.env._target_piece_action_base + 1
        self.assertEqual(int(self.env.legal_actions[pick_src_holder]), 1)
        self.env.step(pick_src_holder)

        # Now choose destination holder (Troops).
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_PIECE)
        pick_dest_holder = self.env._target_piece_action_base + 0
        self.assertEqual(int(self.env.legal_actions[pick_dest_holder]), 1)
        self.env.step(pick_dest_holder)

        # Cash moved from Police holder to Troop holder.
        self.assertEqual(int(sp.cash_holders[1]), 0)
        self.assertEqual(int(sp.cash_holders[0]), 1)
        # Ownership preserved.
        self.assertEqual(int(sp.cash_owner_by_holder[0]), 3)
        self.assertEqual(int(sp.cash[3]), 1)

        # Stop transfers.
        stop_action = self.env._target_piece_action_base + (self.env._target_piece_action_count - 1)
        self.assertEqual(int(self.env.legal_actions[stop_action]), 1)
        self.env.step(stop_action)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
