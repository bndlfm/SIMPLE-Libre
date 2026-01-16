import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_TARGET_FACTION,
)


@unittest.skip("Covered by tests/cubalibre/test_card_21_fangio.py")
class TestFangioShadedTwoSpacesOptionChoice(unittest.TestCase):
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

    def test_fangio_shaded_two_space_sequence(self):
        d = EVENT_DECK_DATA[21]
        self.env.current_card = Card(21, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        # Two eligible casino spaces
        s1 = 3  # Havana
        s2 = 5  # Las Villas

        # Make them qualify as "spaces with any Casinos"
        self.env.board.spaces[s1].closed_casinos = 1
        self.env.board.spaces[s2].pieces[10] = 1

        # Make cash placement legal by having a cube/guerrilla in s2
        self.env.board.spaces[s2].pieces[0] = 1

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        # Pick first space
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick1 = self.env._target_space_action_base + s1
        self.assertEqual(self.env.legal_actions[pick1], 1)
        self.env.step(pick1)

        # Choose option for first space: open casino
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        choose_open = self.env._event_option_action_base + 0
        self.assertEqual(self.env.legal_actions[choose_open], 1)
        self.env.step(choose_open)

        self.assertEqual(self.env.board.spaces[s1].closed_casinos, 0)
        self.assertEqual(self.env.board.spaces[s1].pieces[10], 1)

        # Pick second space
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick2 = self.env._target_space_action_base + s2
        self.assertEqual(self.env.legal_actions[pick2], 1)
        self.env.step(pick2)

        # Choose option for second space: place cash
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        choose_cash = self.env._event_option_action_base + 1
        self.assertEqual(self.env.legal_actions[choose_cash], 1)

        self.env.step(choose_cash)

        # Must now choose which faction owns the Cash marker (Govt allowed because a cube is present).
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        choose_govt = self.env._target_faction_action_base + 0
        self.assertEqual(self.env.legal_actions[choose_govt], 1)

        before_cash = int(self.env.board.spaces[s2].cash[0])
        self.env.step(choose_govt)
        after_cash = int(self.env.board.spaces[s2].cash[0])

        self.assertEqual(after_cash, before_cash + 1)


if __name__ == "__main__":
    unittest.main()
