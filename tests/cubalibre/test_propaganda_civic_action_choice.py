import unittest

from app.environments.cubalibre.envs.classes import Card, PropagandaCard
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, MAIN_PASS, PHASE_CHOOSE_TARGET_SPACE


class TestPropagandaCivicActionChoice(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.sabotage = False
            sp.update_control()

    def test_civic_action_allows_target_choice(self):
        havana = self.env.board.spaces[3]
        havana.pieces[0] = 1
        havana.pieces[1] = 1
        havana.terror = 1
        havana.update_control()

        self.env.players[0].resources = 4

        self.env.propaganda_cards_played = 3
        next_card_data = EVENT_DECK_DATA[1]
        self.env.deck.cards = [
            Card(1, next_card_data["name"], next_card_data["order"], next_card_data["unshaded"], next_card_data["shaded"]),
            PropagandaCard(999),
        ]

        ok = self.env.draw_next_card()
        self.assertFalse(ok)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        action = self.env._target_space_action_base + havana.id
        self.assertEqual(self.env.legal_actions[action], 1)

        self.env.step(action)

        self.assertEqual(havana.terror, 0)
        self.assertEqual(self.env.players[0].resources, 0)

        # Finish Propaganda with a pass if still in civic action.
        if self.env.phase == PHASE_CHOOSE_TARGET_SPACE:
            self.env.step(self.env._main_action_base + MAIN_PASS)


if __name__ == "__main__":
    unittest.main()
