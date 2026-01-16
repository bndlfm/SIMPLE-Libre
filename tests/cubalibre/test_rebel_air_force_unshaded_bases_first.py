import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, MAIN_EVENT, EVENT_UNSHADED, PHASE_CHOOSE_TARGET_SPACE


class TestRebelAirForceUnshadedBasesFirst(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        # Clear board
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

    @unittest.skip("Covered by tests/cubalibre/test_card_44_rebel_air_force.py")
    def test_free_ambush_removes_bases_first(self):
        d = EVENT_DECK_DATA[44]
        self.env.current_card = Card(44, d["name"], d["order"], d["unshaded"], d["shaded"])

        # Force M26 as executing faction
        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 11  # Sierra Maestra
        # Any guerrilla (active or underground) qualifies
        self.env.board.spaces[target].pieces[3] = 1
        # Govt base should be removed before cubes
        self.env.board.spaces[target].govt_bases = 1
        self.env.board.spaces[target].pieces[0] = 2

        before_bases = int(self.env.board.spaces[target].govt_bases)
        before_cubes = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_target = self.env._target_space_action_base + target
        self.assertEqual(self.env.legal_actions[pick_target], 1)
        self.env.step(pick_target)

        after_bases = int(self.env.board.spaces[target].govt_bases)
        after_cubes = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self.assertEqual(after_bases, max(0, before_bases - 1))
        # If there was a second kill, it should come from cubes.
        self.assertLessEqual(after_cubes, before_cubes)


if __name__ == "__main__":
    unittest.main()
