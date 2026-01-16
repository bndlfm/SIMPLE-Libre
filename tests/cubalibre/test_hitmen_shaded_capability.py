import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    OP_ASSASSINATE_DR,
)


class TestHitmenShadedCapability(unittest.TestCase):
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

    def test_hitmen_shaded_enables_syndicate_assassinate_sa(self):
        # Activate capability directly (event handler just adds this flag).
        self.env.capabilities.add("Hitmen_Shaded")

        target = 3  # Havana
        self.env.board.spaces[target].pieces[8] = 1  # Syndicate Underground (required for SA)
        self.env.board.spaces[target].pieces[0] = 1  # Troop to be removed

        self.env.current_player_num = 3
        self.env.players[3].eligible = True
        self.env.players[3].resources = 10
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
        self.env.card_action_slot = 0

        assassinate_sa = self.env._ops_action_base + (OP_ASSASSINATE_DR * self.env.num_spaces) + target
        self.assertEqual(int(self.env.legal_actions[assassinate_sa]), 1)

        before = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])
        self.env.step(assassinate_sa)
        after = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self.assertEqual(after, max(0, before - 1))
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
