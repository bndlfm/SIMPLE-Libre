import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestFatButcherShadedOpenChoiceTargetSelection(unittest.TestCase):
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

    def test_fat_butcher_shaded_ambush_then_choose_where_to_open(self):
        d = EVENT_DECK_DATA[41]
        self.env.current_card = Card(41, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        ambush_space = 3  # Havana
        open_space = 5    # Las Villas

        # Make ambush legal
        self.env.board.spaces[ambush_space].pieces[8] = 1  # SYN underground
        self.env.board.spaces[ambush_space].pieces[0] = 2  # GOVT troops

        # Create a closed casino somewhere else to force OPEN selection stage.
        self.env.board.spaces[open_space].closed_casinos = 1

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_ambush = self.env._target_space_action_base + ambush_space
        self.assertEqual(self.env.legal_actions[pick_ambush], 1)
        self.env.step(pick_ambush)

        # Should now be in OPEN stage selection.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_open = self.env._target_space_action_base + open_space
        self.assertEqual(self.env.legal_actions[pick_open], 1)

        before_closed = int(self.env.board.spaces[open_space].closed_casinos)
        before_open = int(self.env.board.spaces[open_space].pieces[10])

        self.env.step(pick_open)

        after_closed = int(self.env.board.spaces[open_space].closed_casinos)
        after_open = int(self.env.board.spaces[open_space].pieces[10])

        self.assertEqual(after_closed, before_closed - 1)
        self.assertEqual(after_open, before_open + 1)


if __name__ == "__main__":
    unittest.main()
