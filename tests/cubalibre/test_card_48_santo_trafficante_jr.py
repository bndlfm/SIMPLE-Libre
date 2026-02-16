import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_MAIN,
)


class TestCard48SantoTrafficanteJr(unittest.TestCase):
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

    def test_unshaded_reduces_syndicate_resources_and_activates_all_syn_guerrillas(self):
        # Unshaded: Syndicate Resources –10. All Syn Guerrillas Active.
        self._set_card(48)

        # Put Syn resources above 10 so the reduction is observable.
        self.env.players[3].resources = 15

        # Put underground + active Syn guerrillas in a couple spaces.
        s1 = 3
        s2 = 12
        self.env.board.spaces[s1].pieces[8] = 2
        self.env.board.spaces[s1].pieces[9] = 1
        self.env.board.spaces[s2].pieces[8] = 1

        self._start_event(shaded=False, acting_player=0)

        self.assertEqual(int(self.env.players[3].resources), 5)
        self.assertEqual(int(self.env.board.spaces[s1].pieces[8]), 0)
        self.assertEqual(int(self.env.board.spaces[s1].pieces[9]), 3)
        self.assertEqual(int(self.env.board.spaces[s2].pieces[8]), 0)
        self.assertEqual(int(self.env.board.spaces[s2].pieces[9]), 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_shaded_adds_capability(self):
        # Shaded: Capability - Underground Syn block Skim.
        self._set_card(48)

        self.assertNotIn("Trafficante_Shaded", self.env.capabilities)
        self._start_event(shaded=True, acting_player=0)
        self.assertIn("Trafficante_Shaded", self.env.capabilities)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
