import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_MAIN,
)
from app.environments.cubalibre.envs.events import resolve_event
from app.environments.cubalibre.envs.constants import (
    US_ALLIANCE_EMBARGOED,
    US_ALLIANCE_FIRM,
    US_ALLIANCE_RELUCTANT,
)


class TestAidAndAllianceEvents(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def _set_current_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def test_matthews_unshaded_aid_minus_6(self):
        self.env.aid = 15
        self.env.players[1].resources = 0
        self._set_current_card(37)
        resolve_event(self.env, 37, play_shaded=False)
        self.assertEqual(self.env.aid, 9)
        self.assertEqual(int(self.env.players[1].resources), 5)

    def test_matthews_shaded_aid_plus_10_dr_plus_3_syn_plus_5(self):
        self.env.aid = 0
        self.env.players[2].resources = 48
        self.env.players[3].resources = 47
        self._set_current_card(37)
        resolve_event(self.env, 37, play_shaded=True)
        self.assertEqual(int(self.env.aid), 10)
        # Resources clamp at 49.
        self.assertEqual(int(self.env.players[2].resources), 49)
        self.assertEqual(int(self.env.players[3].resources), 49)

    def test_ambassador_smith_shaded_improves_alliance_and_aid_plus_9(self):
        self.env.us_alliance = US_ALLIANCE_EMBARGOED
        self.env.aid = 0
        self._set_current_card(40)
        resolve_event(self.env, 40, play_shaded=True)
        self.assertEqual(self.env.us_alliance, US_ALLIANCE_RELUCTANT)
        self.assertEqual(self.env.aid, 9)

    def test_come_comrades_shaded_lesser_of_aid_or_10_then_aid_plus_5(self):
        self.env.aid = 7
        self.env.players[0].resources = 10
        self._set_current_card(15)
        resolve_event(self.env, 15, play_shaded=True)
        self.assertEqual(self.env.players[0].resources, 17)
        self.assertEqual(self.env.aid, 12)

    def test_speaking_tour_shaded_lesser_of_8_or_aid(self):
        self.env.aid = 5
        self.env.players[0].resources = 10
        self._set_current_card(34)
        resolve_event(self.env, 34, play_shaded=True)
        self.assertEqual(self.env.players[0].resources, 15)
        self.assertEqual(self.env.aid, 13)

    def test_fat_butcher_unshaded_aid_minus_8_if_no_open_casino(self):
        # Ensure no casinos on map
        for sp in self.env.board.spaces:
            sp.pieces[10] = 0
            sp.closed_casinos = 0

        self.env.aid = 10
        self._set_current_card(41)
        self.env.current_player_num = 0
        self.env.card_action_slot = 0
        self.env.phase = PHASE_CHOOSE_MAIN
        for p in self.env.players:
            p.eligible = True

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 1)
        self.assertEqual(self.env.aid, 2)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    @unittest.skip("Covered by tests/cubalibre/test_card_9_coup.py")
    def test_coup_shifts_us_alliance_worse_and_better(self):
        self.env.us_alliance = US_ALLIANCE_FIRM
        self._set_current_card(9)
        resolve_event(self.env, 9, play_shaded=False)
        self.assertEqual(self.env.us_alliance, US_ALLIANCE_RELUCTANT)

        resolve_event(self.env, 9, play_shaded=True)
        self.assertEqual(self.env.us_alliance, US_ALLIANCE_FIRM)


if __name__ == "__main__":
    unittest.main()
