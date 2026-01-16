import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestFatButcherUnshadedTargetSelection(unittest.TestCase):
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

    def test_fat_butcher_unshaded_selects_casino_to_close(self):
        d = EVENT_DECK_DATA[41]
        self.env.current_card = Card(41, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 3  # Havana
        self.env.board.spaces[target].pieces[10] = 1

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Must choose between Close Casino vs Aid -8.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        choose_close = self.env._event_option_action_base + 0
        self.assertEqual(self.env.legal_actions[choose_close], 1)
        self.env.step(choose_close)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_target = self.env._target_space_action_base + target
        self.assertEqual(self.env.legal_actions[pick_target], 1)

        self.env.step(pick_target)

        self.assertEqual(self.env.board.spaces[target].pieces[10], 0)
        self.assertEqual(self.env.board.spaces[target].closed_casinos, 1)


if __name__ == "__main__":
    unittest.main()
