import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    OP_AIR_STRIKE,
    OP_KIDNAP_M26,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
)


class TestCard2GuantanamoBay(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

    def test_card_2_guantanamo_unshaded_allows_m26_kidnap_in_sierra_maestra(self):
        d = EVENT_DECK_DATA[2]
        self.env.current_card = Card(2, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 1  # M26
        self.env.players[1].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertIn("Guantanamo_Unshaded", self.env.capabilities)

        # Verify the capability meaningfully affects legal action masking.
        self.env.current_player_num = 1
        self.env.players[1].resources = 5
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

        sierra = 11
        sp = self.env.board.spaces[sierra]
        sp.pieces[2] = 2  # M26 Underground
        sp.pieces[1] = 0  # Police
        sp.update_control()

        action = self.env._ops_action_base + OP_KIDNAP_M26 * self.env.num_spaces + sierra
        self.assertEqual(int(self.env.legal_actions[action]), 1)

    def test_card_2_guantanamo_shaded_allows_air_strike_under_embargo_and_removes_two(self):
        d = EVENT_DECK_DATA[2]
        self.env.current_card = Card(2, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0  # Govt
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

        self.env.step(self.env._event_side_base + EVENT_SHADED)
        self.assertIn("Guantanamo_Shaded", self.env.capabilities)

        self.env.set_us_alliance(2)  # Embargoed
        self.env.current_player_num = 0
        self.env.players[0].resources = 5
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

        sierra = 11
        sp = self.env.board.spaces[sierra]
        sp.type = 3
        sp.pieces[3] = 2  # Active M26 guerrillas
        sp.update_control()

        action = self.env._ops_action_base + OP_AIR_STRIKE * self.env.num_spaces + sierra
        self.assertEqual(int(self.env.legal_actions[action]), 1)

        before = int(sp.pieces[2] + sp.pieces[3] + sp.pieces[4])
        self.env.step(action)
        after = int(sp.pieces[2] + sp.pieces[3] + sp.pieces[4])

        self.assertEqual(after, before - 2)


if __name__ == "__main__":
    unittest.main()
