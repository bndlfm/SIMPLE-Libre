import unittest

from app.environments.cubalibre.envs.classes import Card, PropagandaCard
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import CubaLibreEnv, MAIN_PASS, PHASE_CHOOSE_TARGET_SPACE


class TestPropagandaExpatChoice(unittest.TestCase):
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

    def test_expat_backing_allows_target_choice(self):
        # Final Propaganda round to skip Resources phase.
        self.env.propaganda_cards_played = 3
        self.env.players[0].resources = 0
        self.env.players[1].resources = 0

        target = self.env.board.spaces[12]
        self.env.players[2].available_forces[0] = 1

        next_card_data = EVENT_DECK_DATA[1]
        self.env.deck.cards = [
            Card(1, next_card_data["name"], next_card_data["order"], next_card_data["unshaded"], next_card_data["shaded"]),
            PropagandaCard(999),
        ]

        ok = self.env.draw_next_card()
        self.assertFalse(ok)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        action = self.env._target_space_action_base + target.id
        self.assertEqual(self.env.legal_actions[action], 1)

        self.env.step(action)

        self.assertEqual(target.pieces[5], 1)

        if self.env.phase == PHASE_CHOOSE_TARGET_SPACE:
            self.env.step(self.env._main_action_base + MAIN_PASS)


if __name__ == "__main__":
    unittest.main()
