import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    MAIN_OPS,
    MAIN_PASS,
    EVENT_SHADED,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    OP_ASSAULT,
    OP_RALLY_M26,
)


class TestEligibilityLimitedOpsRules(unittest.TestCase):
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
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

        self.env.current_card = Card(2, "Test", [0, 1, 2, 3], "un", "sh")
        self.env.card_action_slot = 0
        self.env._card_order_index = 0
        self.env.current_player_num = 0
        self.env.phase = PHASE_CHOOSE_MAIN

    def test_second_actor_limited_ops_after_first_event(self):
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.card_action_slot, 1)
        self.assertEqual(self.env.current_player_num, 1)
        mask = self.env.legal_actions
        self.assertEqual(int(mask[self.env._main_action_base + MAIN_EVENT]), 0)
        self.assertEqual(int(mask[self.env._main_action_base + MAIN_OPS]), 0)
        self.assertEqual(int(mask[self.env._limited_main_action_id]), 1)
        self.assertEqual(int(mask[self.env._main_action_base + MAIN_PASS]), 1)

    def test_second_actor_event_or_limited_after_first_ops(self):
        sp = self.env.board.spaces[3]
        sp.pieces[0] = 2
        sp.pieces[2] = 1
        sp.update_control()

        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        assault_action = self.env._ops_action_base + (OP_ASSAULT * 13 + sp.id)
        self.env.step(assault_action)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        self.env.step(self.env._main_action_base + MAIN_PASS)

        self.assertEqual(self.env.card_action_slot, 1)
        self.assertEqual(self.env.current_player_num, 1)
        mask = self.env.legal_actions
        self.assertEqual(int(mask[self.env._main_action_base + MAIN_EVENT]), 1)
        self.assertEqual(int(mask[self.env._main_action_base + MAIN_OPS]), 0)
        self.assertEqual(int(mask[self.env._limited_main_action_id]), 1)

    def test_second_actor_full_choice_after_first_pass(self):
        self.env.step(self.env._main_action_base + MAIN_PASS)

        self.assertEqual(self.env.card_action_slot, 0)
        self.assertEqual(self.env.current_player_num, 1)
        mask = self.env.legal_actions
        self.assertEqual(int(mask[self.env._main_action_base + MAIN_EVENT]), 1)
        self.assertEqual(int(mask[self.env._main_action_base + MAIN_OPS]), 1)
        self.assertEqual(int(mask[self.env._limited_main_action_id]), 0)

    def test_limited_op_does_not_offer_special_activity(self):
        self.env.players[1].resources = 2

        sp = self.env.board.spaces[3]
        sp.pieces[0] = 2
        sp.pieces[2] = 1
        sp.update_control()

        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        assault_action = self.env._ops_action_base + (OP_ASSAULT * 13 + sp.id)
        self.env.step(assault_action)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        self.env.step(self.env._main_action_base + MAIN_PASS)

        self.assertEqual(self.env.current_player_num, 1)
        self.env.step(self.env._limited_main_action_id)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_LIMITED_OP_ACTION)

        rally_action = self.env._limited_ops_action_base + (OP_RALLY_M26 * 13 + 3)
        self.env.step(rally_action)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertIsNone(self.env._pending_sa)


if __name__ == "__main__":
    unittest.main()
