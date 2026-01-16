import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    OP_MARCH_DR,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestMorganUnshadedMarchRange(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.update_control()

    def _apply_morgan_unshaded(self):
        d = EVENT_DECK_DATA[28]
        self.env.current_card = Card(28, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + 1)  # MAIN_EVENT
        self.env.step(self.env._event_side_base + 0)  # EVENT_UNSHADED

    def test_morgan_unshaded_adds_capability(self):
        self._apply_morgan_unshaded()
        self.assertIn("Morgan_Unshaded", self.env.capabilities)

    def test_march_allows_two_space_source_with_capability(self):
        self.env.current_player_num = 2  # DR
        self.env.players[2].eligible = True
        self.env.players[2].resources = 1
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        src = 0
        self.env.board.spaces[src].pieces[5] = 1  # DR Underground

        dist = self.env._shortest_space_distances(src)
        dest = None
        for sp in self.env.board.spaces:
            if dist.get(sp.id, 999) == 2:
                dest = sp.id
                break
        self.assertIsNotNone(dest)

        march_action = self.env._ops_action_base + (OP_MARCH_DR * self.env.num_spaces) + dest
        self.assertEqual(self.env.legal_actions[march_action], 0)

        self.env.capabilities.add("Morgan_Unshaded")
        self.assertEqual(self.env.legal_actions[march_action], 1)

        self.env.step(march_action)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_source = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[pick_source], 1)


if __name__ == "__main__":
    unittest.main()
