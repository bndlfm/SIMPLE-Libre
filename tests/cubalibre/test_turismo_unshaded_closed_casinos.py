import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv
from app.environments.cubalibre.envs.env import PHASE_CHOOSE_EVENT_SIDE


class TestTurismoUnshadedClosedCasinos(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv()
        self.env.reset()

    def set_card(self, card_id):
        data = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(
            card_id,
            data["name"],
            data["order"],
            data["unshaded"],
            data["shaded"],
        )
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

    def test_turismo_unshaded_shifts_closed_casino_space_toward_neutral(self):
        # Card 39 (Turismo, Un): Support 1 level toward Neutral each Casino space.
        # A space with a CLOSED casino should count as a Casino space.
        s_id = 3  # Havana (City)
        sp = self.env.board.spaces[s_id]

        # Make this a Support space so the shift is visible.
        sp.alignment = 1
        sp.support_active = True

        # Close a casino in this space (no open casinos).
        sp.pieces[10] = 0
        sp.closed_casinos = 1

        self.set_card(39)
        self.env.step(self.env._event_side_base + 0)  # Unshaded

        # Active Support -> Passive Support (1 step toward Neutral)
        self.assertEqual(sp.alignment, 1)
        self.assertFalse(sp.support_active)


if __name__ == "__main__":
    unittest.main()
