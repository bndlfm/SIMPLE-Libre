import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    MAIN_OPS,
    OP_ASSAULT,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard6Mosquera(unittest.TestCase):
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

    def test_card_6_mosquera_unshaded_removes_all_troops_from_mountain(self):
        d = EVENT_DECK_DATA[6]
        self.env.current_card = Card(6, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 1  # M26
        self.env.players[1].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        target = 11
        self.env.board.spaces[target].type = 3
        self.env.board.spaces[target].pieces[0] = 5
        self.env.board.spaces[target].update_control()

        other_mountain = 5
        self.env.board.spaces[other_mountain].type = 3
        self.env.board.spaces[other_mountain].pieces[0] = 0
        self.env.board.spaces[other_mountain].update_control()

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_target = self.env._target_space_action_base + target
        pick_other = self.env._target_space_action_base + other_mountain

        self.assertEqual(int(self.env.legal_actions[pick_target]), 1)
        self.assertEqual(int(self.env.legal_actions[pick_other]), 0)

        available_before = int(self.env.players[0].available_forces[0])
        self.env.step(pick_target)

        sp = self.env.board.spaces[target]
        self.assertEqual(int(sp.pieces[0]), 0)
        self.assertEqual(int(self.env.players[0].available_forces[0]), available_before + 5)

    def test_card_6_mosquera_shaded_mountain_assault_is_unrestricted(self):
        d = EVENT_DECK_DATA[6]
        self.env.current_card = Card(6, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0  # Govt
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

        self.env.step(self.env._event_side_base + EVENT_SHADED)
        self.assertIn("Mosquera_Shaded", self.env.capabilities)

        # New card context for Ops (event play makes Govt ineligible for rest of card).
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        mountain = 11
        sp = self.env.board.spaces[mountain]
        sp.type = 3
        sp.pieces[0] = 3  # Troops
        sp.pieces[3] = 2  # M26 Active (so Troops can hit them)
        sp.update_control()

        enter_ops = self.env._main_action_base + MAIN_OPS
        self.assertEqual(int(self.env.legal_actions[enter_ops]), 1)
        self.env.step(enter_ops)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        assault = self.env._ops_action_base + OP_ASSAULT * self.env.num_spaces + mountain
        self.assertEqual(int(self.env.legal_actions[assault]), 1)

        before = int(sp.pieces[2] + sp.pieces[3])
        self.env.step(assault)
        after = int(sp.pieces[2] + sp.pieces[3])

        # Restricted mountain assault would only kill 1; Mosquera_Shaded should allow killing more.
        self.assertLessEqual(after, before - 2)


if __name__ == "__main__":
    unittest.main()
