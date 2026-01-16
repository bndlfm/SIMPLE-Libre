import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)
from app.environments.cubalibre.envs.events import resolve_event


class TestCasinosOpenClosed(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def _set_current_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    @unittest.skip("Covered by tests/cubalibre/test_card_45_anastasia.py")
    def test_anastasia_closes_open_casinos_into_closed_pool(self):
        havana = self.env.board.spaces[3]
        havana.pieces[10] = 2
        havana.closed_casinos = 0
        havana.update_control()

        self._set_current_card(45)
        resolve_event(self.env, 45, play_shaded=False)

        self.assertEqual(int(havana.pieces[10]), 0)
        self.assertEqual(int(havana.closed_casinos), 2)

    def test_fat_butcher_shaded_opens_a_closed_casino(self):
        ambush_sp = self.env.board.spaces[0]
        ambush_sp.pieces[0] = 1
        ambush_sp.pieces[8] = 1
        ambush_sp.update_control()

        sp = self.env.board.spaces[3]
        sp.pieces[10] = 0
        sp.closed_casinos = 1
        sp.update_control()

        self._set_current_card(41)
        self.env.current_player_num = 0
        self.env.card_action_slot = 0
        self.env.phase = PHASE_CHOOSE_MAIN
        for p in self.env.players:
            p.eligible = True

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + ambush_sp.id)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + sp.id)

        self.assertEqual(int(sp.pieces[10]), 1)
        self.assertEqual(int(sp.closed_casinos), 0)

    def test_reset_opens_closed_casinos(self):
        sp = self.env.board.spaces[3]
        sp.pieces[10] = 0
        sp.closed_casinos = 1
        sp.update_control()

        # Not final propaganda
        self.env.propaganda_cards_played = 1
        self.env.resolve_propaganda()

        self.assertEqual(int(sp.pieces[10]), 1)
        self.assertEqual(int(sp.closed_casinos), 0)


if __name__ == "__main__":
    unittest.main()
