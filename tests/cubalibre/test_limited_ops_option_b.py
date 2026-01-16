import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    MAIN_OPS,
    MAIN_PASS,
    OP_KIDNAP_M26,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
)


class TestLimitedOpsOptionB(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        # Use a real card order so turn-pointer behaves naturally.
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        for p in self.env.players:
            p.eligible = True

    def test_second_actor_only_has_limited_ops_entry_in_main_phase(self):
        # Put us on slot 1 (second actor)
        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"
        self.env.phase = 0

        mask = self.env.legal_actions

        # PASS is always allowed
        self.assertEqual(mask[self.env._main_action_base + MAIN_PASS], 1)

        # Event and normal ops should be disallowed
        self.assertEqual(mask[self.env._main_action_base + MAIN_EVENT], 1)
        self.assertEqual(mask[self.env._main_action_base + MAIN_OPS], 0)

        # Limited ops entry should be allowed
        self.assertEqual(mask[self.env._limited_main_action_id], 1)

    def test_limited_ops_masks_out_kidnap_special_activity(self):
        # Make Kidnap normally legal by setting M26 active in Havana and Govt resources.
        self.env.current_player_num = 1  # M26
        self.env.players[1].resources = 5
        self.env.players[0].resources = 2

        havana = self.env.board.spaces[3]
        havana.pieces[:] = 0
        havana.pieces[2] = 1
        havana.pieces[0] = 1
        havana.update_control()

        # Enter limited ops phase
        self.env.card_action_slot = 1
        self.env.card_first_action = "OPS"
        self.env.phase = 0
        self.env.step(self.env._limited_main_action_id)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_LIMITED_OP_ACTION)

        # Kidnap action should be masked out in limited ops
        kidnap_action = self.env._limited_ops_action_base + (OP_KIDNAP_M26 * self.env.num_spaces) + 3
        mask = self.env.legal_actions
        self.assertEqual(mask[kidnap_action], 0)


if __name__ == "__main__":
    unittest.main()
