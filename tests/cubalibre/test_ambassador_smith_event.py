import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.constants import US_ALLIANCE_EMBARGOED, US_ALLIANCE_FIRM
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    EVENT_SHADED,
    PHASE_CHOOSE_MAIN,
)


class TestAmbassadorSmithEvent(unittest.TestCase):
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
            sp.update_control()

    def test_ambassador_smith_unshaded_us_alliance_down_aid_unchanged(self):
        d = EVENT_DECK_DATA[40]
        self.env.current_card = Card(40, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        self.env.set_us_alliance(US_ALLIANCE_FIRM)
        self.env.set_aid(10)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(int(self.env.us_alliance), 1)
        self.assertEqual(int(self.env.aid), 10)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_ambassador_smith_shaded_us_alliance_up_aid_plus_9_and_syn_gain(self):
        d = EVENT_DECK_DATA[40]
        self.env.current_card = Card(40, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        # Force a legal "improve" (shift toward Firm) by starting at Embargoed.
        self.env.set_us_alliance(US_ALLIANCE_EMBARGOED)
        self.env.set_aid(10)
        self.env.players[3].resources = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        # Alliance improves one step: Embargoed (2) -> Reluctant (1)
        self.assertEqual(int(self.env.us_alliance), US_ALLIANCE_EMBARGOED - 1)
        # Aid +9
        self.assertEqual(int(self.env.aid), 19)
        # Syndicate + min(9, half Aid rounded down) after the increase: min(9, 19//2=9) => 9
        self.assertEqual(int(self.env.players[3].resources), 9)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
