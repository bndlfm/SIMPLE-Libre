import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.constants import (
    US_ALLIANCE_EMBARGOED,
    US_ALLIANCE_FIRM,
    US_ALLIANCE_RELUCTANT,
)
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_UNSHADED,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard11BatistaFlees(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def _set_current_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def test_batista_flees_unshaded_shifts_alliance_worse_and_aid_plus_10(self):
        self.env.us_alliance = US_ALLIANCE_FIRM
        self.env.aid = 0
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env._roll_die = lambda: 1

        self._set_current_card(11)

        target_space = 0
        self.env.board.spaces[target_space].pieces[0] = 1

        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + target_space)

        self.assertEqual(self.env.us_alliance, US_ALLIANCE_RELUCTANT)
        self.assertEqual(self.env.aid, 10)

    def test_batista_flees_unshaded_removes_die_roll_troops_and_redeploys(self):
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 20

        # Put troops into multiple spaces so selection is meaningful.
        for i in range(5):
            self.env.board.spaces[i].pieces[0] = 2

        # Add troops elsewhere to test redeploy pulls them into a govt-controlled city/base.
        self.env.board.spaces[11].pieces[0] = 1  # Sierra Maestra (mountain)

        self.env.us_alliance = US_ALLIANCE_RELUCTANT
        self.env.aid = 0

        self.env._roll_die = lambda: 3
        self._set_current_card(11)

        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.players[0].resources, 10)

        removed = 0
        while self.env.phase == PHASE_CHOOSE_TARGET_SPACE:
            # always pick the first space with troops
            target = next(i for i, sp in enumerate(self.env.board.spaces) if sp.pieces[0] > 0)
            before = int(self.env.board.spaces[target].pieces[0])
            self.env.step(self.env._target_space_action_base + target)
            after = int(self.env.board.spaces[target].pieces[0])
            if after < before:
                removed += 1

        self.assertEqual(removed, 3)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

        # Event finishes by worsening alliance (unless already Embargoed), +10 Aid, and doing Govt redeploy.
        self.assertEqual(self.env.us_alliance, US_ALLIANCE_EMBARGOED)
        self.assertEqual(self.env.aid, 10)


if __name__ == "__main__":
    unittest.main()
