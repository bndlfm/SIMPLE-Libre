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


class TestCard26RodriguezLoeches(unittest.TestCase):
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

    def _start_event(self, shaded, acting_player=0):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_places_one_dr_guerrilla_and_offers_free_march_rally_or_ambush(self):
        # Card 26 (Rodríguez Loeches, Un): DR places 1 Guerrilla anywhere then free March/Rally/Ambush there.
        self._set_card(26)

        # Ensure placement is possible
        self.env.players[2].available_forces[0] = 5

        place_id = 1

        self._start_event(shaded=False, acting_player=0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + place_id)
        self.assertEqual(int(self.env.board.spaces[place_id].pieces[5]), 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        pending_opt = self.env._pending_event_option
        self.assertEqual(pending_opt["event"], "LOECHES_UN")

        allowed = list(pending_opt.get("allowed", []))
        # Rally and Ambush should always be present; March depends on adjacent DR guerrillas.
        self.assertIn(1, allowed)
        self.assertIn(2, allowed)

        # Take Rally option (1)
        self.env.step(self.env._event_option_action_base + 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_shaded_removes_one_dr_guerrilla_and_dr_resources_minus_5(self):
        # Card 26 (Rodríguez Loeches, Sh): Remove 1 DR Guerrilla. DR Resources –5.
        self._set_card(26)

        self.env.board.spaces[0].pieces[5] = 1
        self.env.players[2].resources = 10

        self._start_event(shaded=True, acting_player=0)
        self.assertEqual(int(self.env.players[2].resources), 5)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(int(self.env.board.spaces[0].pieces[5]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
