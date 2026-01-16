import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_OPS,
    MAIN_PASS,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    OP_RALLY_M26,
)


class TestOpsSaConsumesOneSlot(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_ops_then_skip_sa_consumes_one_slot(self):
        # Use a deterministic event card.
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        # Force M26 as the acting player in slot 0.
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.players[1].resources = 10

        # Make a special activity legal after the Op so SA phase is actually entered.
        havana = 3
        self.env.board.spaces[havana].pieces[3] = 1  # active M26 so Kidnap is legal in a city

        enter_ops = self.env._main_action_base + MAIN_OPS
        self.assertEqual(self.env.legal_actions[enter_ops], 1)
        self.env.step(enter_ops)

        rally = self.env._ops_action_base + OP_RALLY_M26 * self.env.num_spaces + havana
        self.assertEqual(self.env.legal_actions[rally], 1)
        self.env.step(rally)

        # Op should transition into SA phase and not consume slot yet.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        self.assertEqual(self.env.card_action_slot, 0)

        skip_sa = self.env._main_action_base + MAIN_PASS
        self.assertEqual(self.env.legal_actions[skip_sa], 1)
        self.env.step(skip_sa)

        # Skip consumes the action slot.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertEqual(self.env.card_action_slot, 1)


if __name__ == "__main__":
    unittest.main()
