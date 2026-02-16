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
    OP_RALLY_M26,
)


class TestCard30TheGuerrillaLife(unittest.TestCase):
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

    def _start_event(self, shaded, acting_player=1):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_event_adds_capability(self):
        # Card 30 (The Guerrilla Life, Un): Adds capability affecting M26 Rallies.
        self._set_card(30)
        self._start_event(shaded=False, acting_player=1)
        self.assertIn("GuerrillaLife_Unshaded", self.env.capabilities)

    def test_unshaded_m26_rally_flips_actives_even_when_placing(self):
        # With GuerrillaLife_Unshaded, M26 Rally flips any Active guerrillas Underground even if placing.
        self.env.capabilities.add("GuerrillaLife_Unshaded")

        space_id = 0  # Pinar Del Rio (Province)
        sp = self.env.board.spaces[space_id]
        sp.pieces[3] = 1  # M26 Active
        self.assertTrue(self.env._add_cash_marker(sp, 1, preferred_idx=3))

        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.players[1].resources = 10
        self.env.players[1].available_forces[0] = 3
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        action = self.env._ops_action_base + OP_RALLY_M26 * self.env.num_spaces + space_id
        self.assertEqual(int(self.env.legal_actions[action]), 1)
        self.env.step(action)

        self.assertEqual(int(sp.pieces[3]), 0)
        self.assertGreaterEqual(int(sp.pieces[2]), 2)
        self.assertEqual(int(sp.cash_holders[2]), 1)

    def test_shaded_flips_all_dr_underground_and_places_in_city(self):
        # Card 30 (The Guerrilla Life, Sh): Flip all DR guerrillas underground, then place 1 DR guerrilla in a City.
        self._set_card(30)

        self.env.board.spaces[0].pieces[6] = 2  # 2 Active DR in Pinar

        self._start_event(shaded=True, acting_player=2)
        self.assertEqual(int(self.env.board.spaces[0].pieces[5]), 2)
        self.assertEqual(int(self.env.board.spaces[0].pieces[6]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + 3)  # Havana (City)
        self.assertGreaterEqual(int(self.env.board.spaces[3].pieces[5]), 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_shaded_no_available_dr_guerrillas_disallows_city_target(self):
        # If DR has no available guerrillas, no city should be targetable.
        self._set_card(30)
        self.env.players[2].available_forces[0] = 0

        self._start_event(shaded=True, acting_player=2)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick = self.env._target_space_action_base + 3
        self.assertEqual(int(self.env.legal_actions[pick]), 0)
        self.assertEqual(int(self.env.players[2].available_forces[0]), 0)


if __name__ == "__main__":
    unittest.main()
