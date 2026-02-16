import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_TARGET_SPACE,
    OP_MARCH_DR,
)


class TestCard28Morgan(unittest.TestCase):
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

    def _set_card(self, card_id):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def _start_event(self, shaded, acting_player=2):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_event_adds_capability(self):
        # Card 28 (Morgan, Un): Adds capability affecting DR March range.
        self._set_card(28)
        self._start_event(shaded=False, acting_player=2)
        self.assertIn("Morgan_Unshaded", self.env.capabilities)

    def test_unshaded_dr_march_can_target_within_2_spaces(self):
        # With Morgan_Unshaded, DR March may reach spaces within distance 2.
        self.env.capabilities.add("Morgan_Unshaded")

        # Put a DR guerrilla in Pinar (0); target a March destination of Matanzas (4), dist=2.
        src_id = 0
        dest_id = 4
        self.env.board.spaces[src_id].pieces[5] = 1

        self.env.current_player_num = 2
        self.env.players[2].eligible = True
        self.env.players[2].resources = 10
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        action = self.env._ops_action_base + OP_MARCH_DR * self.env.num_spaces + dest_id
        self.assertEqual(int(self.env.legal_actions[action]), 1)

        self.env.step(action)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # In MARCH_SRC stage, src_id should be a legal selection because it's within range 2 of dest.
        pick_src = self.env._target_space_action_base + src_id
        self.assertEqual(int(self.env.legal_actions[pick_src]), 1)

    def test_shaded_sets_space_with_dr_guerrilla_to_active_support(self):
        # Card 28 (Morgan, Sh): Set a space with a DR Guerrilla to Active Support.
        self._set_card(28)

        self.env.board.spaces[5].pieces[5] = 1
        self.env.board.spaces[5].alignment = 0

        self._start_event(shaded=True, acting_player=2)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + 5)
        self.assertEqual(int(self.env.board.spaces[5].alignment), 1)
        self.assertTrue(self.env.board.spaces[5].support_active)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
