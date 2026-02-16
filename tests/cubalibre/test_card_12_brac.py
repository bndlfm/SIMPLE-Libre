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
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard12Brac(unittest.TestCase):
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

        d = EVENT_DECK_DATA[12]
        self.env.current_card = Card(12, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

    def test_brac_unshaded_removes_two_guerrillas_with_faction_and_piece_choices(self):
        # Set up a space with multiple guerrilla factions so we must pick faction.
        target = 4
        sp = self.env.board.spaces[target]
        sp.pieces[2] = 1  # M26 Underground
        sp.pieces[5] = 1  # DR Underground
        sp.pieces[6] = 1  # DR Active

        # Also set up a second space with a guerrilla so second removal can target elsewhere.
        target2 = 12
        sp2 = self.env.board.spaces[target2]
        sp2.pieces[8] = 1  # SYN Underground

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + target)

        # Multiple factions present -> choose faction.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        choose_dr = self.env._target_faction_action_base + 2
        self.assertEqual(int(self.env.legal_actions[choose_dr]), 1)
        self.env.step(choose_dr)

        # DR has both active and underground -> choose which to remove.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        remove_active = self.env._event_option_action_base + 1
        self.assertEqual(int(self.env.legal_actions[remove_active]), 1)
        self.env.step(remove_active)

        self.assertEqual(int(sp.pieces[6]), 0)

        # Second removal: still in target selection.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + target2)

        # SYN only -> should remove directly and finish.
        self.assertEqual(int(sp2.pieces[8] + sp2.pieces[9]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_brac_shaded_places_police_and_adds_lesser_of_6_or_aid_to_govt_resources(self):
        self.env.players[0].resources = 0
        self.env.aid = 5
        self.env.players[0].available_forces[1] = 10

        target = 3

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + target)

        sp = self.env.board.spaces[target]
        self.assertEqual(int(sp.pieces[1]), 1)
        self.assertEqual(int(self.env.players[0].resources), 5)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
