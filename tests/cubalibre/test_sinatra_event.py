import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    EVENT_SHADED,
)


class TestSinatraEvent(unittest.TestCase):
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

    def test_sinatra_unshaded_syn_resources_minus_6(self):
        d = EVENT_DECK_DATA[46]
        self.env.current_card = Card(46, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        self.env.players[3].resources = 10
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(int(self.env.players[3].resources), 4)

    def test_sinatra_shaded_places_open_casino_and_syn_cash_with_police(self):
        d = EVENT_DECK_DATA[46]
        self.env.current_card = Card(46, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        havana = 3
        self.env.board.spaces[havana].pieces[10] = 0
        self.env.board.spaces[havana].pieces[1] = 1  # Police holder
        self.env.players[3].available_bases = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        sp = self.env.board.spaces[havana]
        self.assertEqual(int(sp.pieces[10]), 1)
        self.assertEqual(int(sp.cash[3]), 1)
        self.assertEqual(int(sp.cash_holders[1]), 1)


if __name__ == "__main__":
    unittest.main()
