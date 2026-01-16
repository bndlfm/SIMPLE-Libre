import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCantilloShadedEvent(unittest.TestCase):
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
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            sp.update_control()

    def test_cantillo_shaded_free_sweep_then_assault(self):
        d = EVENT_DECK_DATA[3]
        self.env.current_card = Card(3, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

        target = 0

        # Target has Troops and an Underground guerrilla to reveal.
        # After reveal, Assault should kill the now-Active guerrilla.
        self.env.board.spaces[target].pieces[0] = 1  # Troops
        self.env.board.spaces[target].pieces[1] = 1  # Police
        self.env.board.spaces[target].pieces[2] = 1  # M26 Underground
        self.env.board.spaces[target].update_control()

        self.env.step(self.env._event_side_base + EVENT_SHADED)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_target = self.env._target_space_action_base + target
        self.assertEqual(int(self.env.legal_actions[pick_target]), 1)
        self.env.step(pick_target)

        # Should complete the event action and return to main.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertIsNone(self.env._pending_event_target)

        # Guerrilla should have been revealed then killed.
        self.assertEqual(int(self.env.board.spaces[target].pieces[2]), 0)
        self.assertEqual(int(self.env.board.spaces[target].pieces[3]), 0)


if __name__ == "__main__":
    unittest.main()
