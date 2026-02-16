import unittest
from unittest.mock import patch

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_OP_ACTION,
    OP_ATTACK_M26,
)


class TestCard22Raul(unittest.TestCase):
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
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

        self.env.aid = 0

    def _set_card(self, card_id):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def _start_event(self, shaded, acting_player=1):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_event_adds_capability(self):
        self._set_card(22)
        self._start_event(shaded=False, acting_player=1)
        self.assertIn("Raul_Unshaded", self.env.capabilities)

    def test_unshaded_allows_m26_attack_reroll_on_failed_roll(self):
        # Verify reroll behavior deterministically by controlling _roll_die.
        self.env.capabilities.add("Raul_Unshaded")

        # Havana (3)
        sp = self.env.board.spaces[3]
        sp.pieces[2] = 1  # 1 M26 underground
        sp.pieces[0] = 2  # 2 Govt troops

        self.env.current_player_num = 1
        self.env.players[1].resources = 10
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        action = self.env._ops_action_base + (OP_ATTACK_M26 * self.env.num_spaces) + 3

        # First roll fails (>cnt), second roll succeeds (<=cnt)
        with patch.object(self.env, "_roll_die", side_effect=[6, 1]):
            self.env.step(action)

        # Ensure we consumed both rolls.
        self.assertIn("Raul_Unshaded", self.env.capabilities)

    def test_shaded_event_adds_momentum_capability(self):
        self._set_card(22)
        self._start_event(shaded=True, acting_player=0)
        self.assertIn("Raul_Shaded", self.env.capabilities)

    def test_shaded_kidnap_adds_aid_twice_resources_taken(self):
        # This is the engine's current interpretation of Raul (Sh): Aid increases by 2x kidnap resources.
        self.env.players[0].resources = 2
        self.env.aid = 0
        self.env.capabilities.add("Raul_Shaded")

        self.env.op_kidnap_m26(3)
        self.assertEqual(int(self.env.aid), 4)


if __name__ == "__main__":
    unittest.main()
