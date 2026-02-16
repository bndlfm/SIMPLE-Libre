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
from app.environments.cubalibre.envs.constants import US_ALLIANCE_FIRM, US_ALLIANCE_RELUCTANT


class TestCard9Coup(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

        d = EVENT_DECK_DATA[9]
        self.env.current_card = Card(9, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 0

    def test_unshaded_shifts_govt_control_spaces_toward_neutral_and_worsens_us_alliance(self):
        # Card 9 unshaded: shift all Govt controlled spaces 1 step toward Neutral; US Alliance up 1 box.
        self.env.us_alliance = US_ALLIANCE_FIRM

        # Havana controlled by Govt and currently Active Support.
        havana = 3
        sp = self.env.board.spaces[havana]
        sp.pieces[0] = 3
        sp.alignment = 1
        sp.support_active = True
        sp.update_control()
        self.assertEqual(int(sp.controlled_by), 1)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # One level toward neutral: Active Support -> Passive Support.
        self.assertEqual(int(sp.alignment), 1)
        self.assertFalse(bool(sp.support_active))
        self.assertEqual(int(self.env.us_alliance), US_ALLIANCE_RELUCTANT)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_shaded_activates_and_free_assaults_dr_in_cities_with_cubes_and_improves_us_alliance(self):
        # Card 9 shaded: activate + free assault DR pieces in Cities with cubes; US Alliance down 1 box.
        self.env.us_alliance = US_ALLIANCE_RELUCTANT

        havana = 3
        self.env.board.spaces[havana].pieces[0] = 2  # Govt troops (cubes)
        self.env.board.spaces[havana].pieces[5] = 2  # DR underground guerrillas

        santiago = 5
        self.env.board.spaces[santiago].pieces[5] = 2  # DR underground guerrillas, but no cubes => untouched

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(int(self.env.us_alliance), US_ALLIANCE_FIRM)

        # Havana: DR should be assaulted away.
        self.assertEqual(int(self.env.board.spaces[havana].pieces[5]), 0)
        self.assertEqual(int(self.env.board.spaces[havana].pieces[6]), 0)

        # Santiago: unchanged.
        self.assertEqual(int(self.env.board.spaces[santiago].pieces[5]), 2)
        self.assertEqual(int(self.env.board.spaces[santiago].pieces[6]), 0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
