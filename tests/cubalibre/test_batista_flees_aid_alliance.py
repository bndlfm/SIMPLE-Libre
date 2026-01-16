import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.constants import (
    US_ALLIANCE_EMBARGOED,
    US_ALLIANCE_RELUCTANT,
)
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_UNSHADED,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_TARGET_SPACE,
)


@unittest.skip("Covered by tests/cubalibre/test_card_11_batista_flees.py")
class TestBatistaFleesAidAlliance(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_batista_flees_unshaded_improves_alliance_and_aid(self):
        self.env.us_alliance = US_ALLIANCE_EMBARGOED
        self.env.aid = 0
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env._roll_die = lambda: 1

        card_id = 11
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

        target_space = 0
        self.env.board.spaces[target_space].pieces[0] = 1

        action = self.env._event_side_base + EVENT_UNSHADED
        self.env.step(action)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        action = self.env._target_space_action_base + target_space
        self.env.step(action)

        self.assertEqual(self.env.us_alliance, US_ALLIANCE_RELUCTANT)
        self.assertEqual(self.env.aid, 10)


if __name__ == "__main__":
    unittest.main()
