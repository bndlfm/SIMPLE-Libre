import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard19SierraMaestraManifesto(unittest.TestCase):
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

    def _set_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def _start_event(self, shaded: bool, acting_player: int = 0):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_uses_card_order_targets_spaces_with_existing_pieces_and_stays_eligible_next_card(self):
        # Card 19 (Sierra Maestra Manifesto, Un): In card order, each faction may place 2 non-Casino pieces
        # in a space where they already have a piece. Executing faction stays eligible for next card.
        self._set_card(19)

        # Set up one existing piece per faction in different spaces.
        m26_space = 9
        dr_space = 12
        syn_space = 5
        govt_space = 3

        self.env.board.spaces[m26_space].pieces[2] = 1  # M26 underground
        self.env.board.spaces[dr_space].pieces[5] = 1   # DR underground
        self.env.board.spaces[syn_space].pieces[8] = 1  # Syndicate underground
        self.env.board.spaces[govt_space].pieces[0] = 1 # Govt troop
        for sid in [m26_space, dr_space, syn_space, govt_space]:
            self.env.board.spaces[sid].update_control()

        # Give each faction enough available pieces to place 2.
        self.env.players[1].available_forces[0] = 2
        self.env.players[1].available_bases = 0
        self.env.players[2].available_forces[0] = 2
        self.env.players[2].available_bases = 0
        self.env.players[3].available_forces[0] = 2
        self.env.players[0].available_forces[0] = 1
        self.env.players[0].available_forces[1] = 1

        self._start_event(shaded=False, acting_player=0)

        # Card order for 19 is MDSG => [M26, DR, Syndicate, Govt]
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(int(self.env._pending_event_target["f_idx"]), 1)

        # For the first faction (M26), only the space with existing M26 pieces should be targetable.
        self.assertEqual(int(self.env.legal_actions[self.env._target_space_action_base + m26_space]), 1)
        self.assertEqual(int(self.env.legal_actions[self.env._target_space_action_base + 0]), 0)

        # M26 places 2 guerrillas.
        self.env.step(self.env._target_space_action_base + m26_space)
        self.env.step(self.env._target_space_action_base + m26_space)
        self.assertEqual(int(self.env._pending_event_target["f_idx"]), 2)

        # DR places 2.
        self.env.step(self.env._target_space_action_base + dr_space)
        self.env.step(self.env._target_space_action_base + dr_space)
        self.assertEqual(int(self.env._pending_event_target["f_idx"]), 3)

        # Syndicate places 2.
        self.env.step(self.env._target_space_action_base + syn_space)
        self.env.step(self.env._target_space_action_base + syn_space)
        self.assertEqual(int(self.env._pending_event_target["f_idx"]), 0)

        # Govt places 2, but must choose piece type each time.
        self.env.step(self.env._target_space_action_base + govt_space)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 1)  # Police

        self.env.step(self.env._target_space_action_base + govt_space)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 0)  # Troop

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertGreaterEqual(int(self.env.board.spaces[govt_space].pieces[1]), 1)
        self.assertGreaterEqual(int(self.env.board.spaces[govt_space].pieces[0]), 2)

        # Executing faction should not be ineligible on the next card.
        self.assertNotIn(0, self.env.ineligible_next_card)

    def test_shaded_is_noop_event_path(self):
        # Card 19 shaded has no mechanical text in this implementation; ensure it resolves without crashing.
        self._set_card(19)
        self._start_event(shaded=True, acting_player=0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
