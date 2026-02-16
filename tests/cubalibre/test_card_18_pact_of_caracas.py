import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    MAIN_OPS,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    OP_ASSASSINATE_DR,
    OP_KIDNAP_M26,
    OP_TERROR_M26,
)


class TestCard18PactOfCaracas(unittest.TestCase):
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
            if hasattr(sp, "refresh_cash_counts"):
                sp.refresh_cash_counts()
            sp.update_control()

        for p in self.env.players:
            p.eligible = True
            p.resources = 0

    def _set_card(self, card_id):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def test_unshaded_event_adds_capability_and_stays_eligible_next_card(self):
        # Card 18 (Pact of Caracas, Un): adds capability and executing faction stays eligible for next card.
        self._set_card(18)

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertIn("PactOfCaracas_Unshaded", self.env.capabilities)
        self.assertNotIn(0, self.env.ineligible_next_card)

        # Force a next card and confirm eligibility applied.
        next_d = EVENT_DECK_DATA[8]
        self.env.deck.cards = [Card(8, next_d["name"], next_d["order"], next_d["unshaded"], next_d["shaded"])]
        self.env.draw_next_card()
        self.assertTrue(self.env.players[0].eligible)

    def test_shaded_side_is_not_playable(self):
        # data.py shaded text is empty and events.py marks it unplayable.
        self._set_card(18)

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        pick_shaded = self.env._event_side_base + EVENT_SHADED
        self.assertEqual(int(self.env.legal_actions[pick_shaded]), 0)

    def test_pact_blocks_terror_when_not_same_player(self):
        env = CubaLibreEnv(verbose=False, manual=False, same_player_control=False)
        env.reset(seed=123)

        for sp in env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash_holders[:] = 0
            if hasattr(sp, "refresh_cash_counts"):
                sp.refresh_cash_counts()
            sp.update_control()

        env.capabilities.add("PactOfCaracas_Unshaded")
        env.current_player_num = 1
        env.players[1].resources = 10
        env.phase = PHASE_CHOOSE_OP_ACTION
        env.card_action_slot = 0

        space_id = 0
        env.board.spaces[space_id].pieces[2] = 1

        action = env._ops_action_base + OP_TERROR_M26 * env.num_spaces + space_id
        self.assertEqual(int(env.legal_actions[action]), 0)

    def test_pact_allows_terror_when_same_player(self):
        self.env.capabilities.add("PactOfCaracas_Unshaded")
        self.env.current_player_num = 1
        self.env.players[1].resources = 10
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        space_id = 0
        self.env.board.spaces[space_id].pieces[2] = 1

        action = self.env._ops_action_base + OP_TERROR_M26 * self.env.num_spaces + space_id
        self.assertEqual(int(self.env.legal_actions[action]), 1)

        self.env.step(action)
        self.assertEqual(int(self.env.board.spaces[space_id].terror), 1)

    def test_pact_blocks_dr_assassinate_when_not_same_player(self):
        env = CubaLibreEnv(verbose=False, manual=False, same_player_control=False)
        env.reset(seed=123)

        for sp in env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash_holders[:] = 0
            if hasattr(sp, "refresh_cash_counts"):
                sp.refresh_cash_counts()
            sp.update_control()

        env.capabilities.add("PactOfCaracas_Unshaded")
        env.current_player_num = 2  # DR
        env.players[2].resources = 10
        env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
        env.card_action_slot = 0

        space_id = 0
        sp = env.board.spaces[space_id]
        sp.type = 0  # City
        sp.pieces[5] = 2  # DR Underground
        sp.pieces[1] = 1  # Govt Police
        sp.pieces[0] = 1  # Govt Troops
        sp.update_control()

        action = env._ops_action_base + OP_ASSASSINATE_DR * env.num_spaces + space_id
        self.assertEqual(int(env.legal_actions[action]), 0)

    def test_pact_blocks_m26_kidnap_when_not_same_player(self):
        env = CubaLibreEnv(verbose=False, manual=False, same_player_control=False)
        env.reset(seed=123)

        for sp in env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.closed_casinos = 0
            sp.cash_holders[:] = 0
            if hasattr(sp, "refresh_cash_counts"):
                sp.refresh_cash_counts()
            sp.update_control()

        env.capabilities.add("PactOfCaracas_Unshaded")
        env.current_player_num = 1  # M26
        env.players[1].resources = 10
        env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
        env.card_action_slot = 0

        space_id = 0
        sp = env.board.spaces[space_id]
        sp.type = 0  # City
        sp.pieces[2] = 2  # M26 Underground
        sp.pieces[1] = 0  # Govt Police
        sp.pieces[0] = 1  # Govt Troops
        sp.pieces[10] = 1  # open Casino (satisfies Kidnap location)
        sp.update_control()

        action = env._ops_action_base + OP_KIDNAP_M26 * env.num_spaces + space_id
        self.assertEqual(int(env.legal_actions[action]), 0)

    def test_pact_blocks_mafia_offensive_limited_op_terror_when_not_same_player(self):
        env = CubaLibreEnv(verbose=False, manual=False, same_player_control=False)
        env.reset(seed=123)

        for sp in env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash_holders[:] = 0
            if hasattr(sp, "refresh_cash_counts"):
                sp.refresh_cash_counts()
            sp.update_control()

        env.capabilities.add("PactOfCaracas_Unshaded")
        env._pending_mafia_offensive = {"faction": 1}  # M26 is acting in the free LimOp
        env.current_player_num = 1
        env.players[1].resources = 0
        env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        env.card_action_slot = 0

        space_id = 0
        sp = env.board.spaces[space_id]
        sp.pieces[2] = 1  # M26 Underground (enables Terror)
        sp.update_control()

        base = 7
        terror_op = base + 3
        action = env._limited_ops_action_base + terror_op * env.num_spaces + space_id
        self.assertEqual(int(env.legal_actions[action]), 0)

    def test_pact_cancels_when_two_bases_removed_at_once(self):
        # If either faction removes 2 of its bases at once, cancel capability.
        self.env.capabilities.add("PactOfCaracas_Unshaded")

        space_id = 2
        sp = self.env.board.spaces[space_id]
        sp.pieces[4] = 2  # M26 Bases

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 1

        # Begin action tracking
        self.env.step(self.env._main_action_base + MAIN_OPS)

        self.env.board.remove_piece(space_id, 1, 2)
        self.env.board.remove_piece(space_id, 1, 2)

        self.assertNotIn("PactOfCaracas_Unshaded", self.env.capabilities)


if __name__ == "__main__":
    unittest.main()
