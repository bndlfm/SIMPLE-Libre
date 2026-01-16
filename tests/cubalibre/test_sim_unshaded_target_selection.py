import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestSIMUnshadedTargetSelection(unittest.TestCase):
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
            sp.cash[:] = 0
            sp.cash_holders[:] = 0
            sp.update_control()

    def test_sim_unshaded_choose_support_no_police(self):
        d = EVENT_DECK_DATA[4]
        self.env.current_card = Card(4, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 8  # Camaguey City
        non_target = 3  # Havana

        # Target qualifies: Support + no Police
        self.env.board.spaces[target].alignment = 1
        self.env.board.spaces[target].support_active = True
        self.env.board.spaces[target].pieces[1] = 0

        # Non-target: Support but has Police, so should be masked out
        self.env.board.spaces[non_target].alignment = 1
        self.env.board.spaces[non_target].support_active = True
        self.env.board.spaces[non_target].pieces[1] = 1

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_target = self.env._target_space_action_base + target
        pick_non_target = self.env._target_space_action_base + non_target

        self.assertEqual(self.env.legal_actions[pick_target], 1)
        self.assertEqual(self.env.legal_actions[pick_non_target], 0)

        self.env.step(pick_target)

        sp = self.env.board.spaces[target]
        # Active Support should become Passive Support (alignment stays Support, but not active).
        self.assertEqual(int(sp.alignment), 1)
        self.assertFalse(bool(sp.support_active))


if __name__ == "__main__":
    unittest.main()
