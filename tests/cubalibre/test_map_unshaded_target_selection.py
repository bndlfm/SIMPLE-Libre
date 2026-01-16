import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
)


@unittest.skip("Covered by tests/cubalibre/test_card_10_map.py")
class TestMapUnshadedTargetSelection(unittest.TestCase):
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

    def test_map_unshaded_requires_target_cube_space_and_places_two_guerrillas(self):
        d = EVENT_DECK_DATA[10]
        self.env.current_card = Card(10, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 3  # Havana
        self.env.board.spaces[target].pieces[1] = 1  # police cube
        self.env.players[1].available_forces[0] = 10

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_target = self.env._target_space_action_base + target
        self.assertEqual(self.env.legal_actions[pick_target], 1)

        before_m26 = int(self.env.board.spaces[target].pieces[2] + self.env.board.spaces[target].pieces[3])
        before_cubes = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self.env.step(pick_target)

        # Choose factions for the 2 guerrillas (pick M26 twice for determinism).
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        choose_m26 = self.env._target_faction_action_base + 1
        self.assertEqual(self.env.legal_actions[choose_m26], 1)
        self.env.step(choose_m26)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.assertEqual(self.env.legal_actions[choose_m26], 1)
        self.env.step(choose_m26)

        after_m26 = int(self.env.board.spaces[target].pieces[2] + self.env.board.spaces[target].pieces[3])
        after_cubes = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self.assertEqual(after_cubes, max(0, before_cubes - 1))
        self.assertEqual(after_m26, before_m26 + 2)


if __name__ == "__main__":
    unittest.main()
