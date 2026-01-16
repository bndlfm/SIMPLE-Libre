import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    MAIN_OPS,
    MAIN_PASS,
    OP_ASSAULT,
    OP_SWEEP,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard5Masferrer(unittest.TestCase):
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

    def test_card_5_masferrer_unshaded_two_provinces_to_passive_opposition(self):
        d = EVENT_DECK_DATA[5]
        self.env.current_card = Card(5, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

        # Pick a Province with Troops and an adjacent Province.
        src = 0
        dest = 2

        self.env.board.spaces[src].pieces[0] = 1
        self.env.board.spaces[src].alignment = 0

        self.env.board.spaces[dest].alignment = 1

        if dest not in self.env.board.spaces[src].adj_ids:
            self.env.board.spaces[src].adj_ids = list(set(self.env.board.spaces[src].adj_ids + [dest]))
        if src not in self.env.board.spaces[dest].adj_ids:
            self.env.board.spaces[dest].adj_ids = list(set(self.env.board.spaces[dest].adj_ids + [src]))

        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + src)
        self.assertEqual(int(self.env.board.spaces[src].alignment), 2)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + dest)
        self.assertEqual(int(self.env.board.spaces[dest].alignment), 2)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_card_5_masferrer_shaded_adds_capability(self):
        d = EVENT_DECK_DATA[5]
        self.env.current_card = Card(5, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

        # Play shaded to gain capability.
        self.env.step(self.env._event_side_base + EVENT_SHADED)
        self.assertIn("Masferrer_Shaded", self.env.capabilities)

    def test_card_5_masferrer_shaded_capability_free_assault_after_sweep(self):
        # With capability active, Sweep may free Assault 1 space as its Special Activity.
        self.env.capabilities.add("Masferrer_Shaded")

        # Use any card shell; we are testing Ops behavior.
        d = EVENT_DECK_DATA[5]
        self.env.current_card = Card(5, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        havana = 3
        adj = self.env.board.spaces[havana].adj_ids[0]
        self.env.board.spaces[adj].pieces[0] = 1
        self.env.board.spaces[havana].pieces[2] = 1
        self.env.board.spaces[adj].update_control()
        self.env.board.spaces[havana].update_control()

        enter_ops = self.env._main_action_base + MAIN_OPS
        self.assertEqual(int(self.env.legal_actions[enter_ops]), 1)
        self.env.step(enter_ops)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        sweep = self.env._ops_action_base + OP_SWEEP * self.env.num_spaces + havana
        self.assertEqual(int(self.env.legal_actions[sweep]), 1)
        self.env.step(sweep)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_src = self.env._target_space_action_base + adj
        self.assertEqual(int(self.env.legal_actions[pick_src]), 1)
        self.env.step(pick_src)

        move_one = self.env._event_option_action_base + 0
        self.assertEqual(int(self.env.legal_actions[move_one]), 1)
        self.env.step(move_one)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        assault = self.env._ops_action_base + OP_ASSAULT * self.env.num_spaces + havana
        self.assertEqual(int(self.env.legal_actions[assault]), 1)

        before = int(self.env.board.spaces[havana].pieces[2] + self.env.board.spaces[havana].pieces[3])
        self.env.step(assault)
        after = int(self.env.board.spaces[havana].pieces[2] + self.env.board.spaces[havana].pieces[3])

        self.assertLess(after, before)

        # Skip SA cleanup if offered again.
        if self.env.phase == PHASE_CHOOSE_SPECIAL_ACTIVITY:
            self.env.step(self.env._main_action_base + MAIN_PASS)


if __name__ == "__main__":
    unittest.main()
