import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestPactOfMiamiUnshadedRemovalFlow(unittest.TestCase):
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
            sp.update_control()

    def test_pact_of_miami_unshaded_removes_two_guerrillas_via_two_picks(self):
        d = EVENT_DECK_DATA[47]
        self.env.current_card = Card(47, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        s1 = 9   # Oriente
        s2 = 11  # Sierra Maestra
        s_empty = 3  # Havana (no guerrillas)

        # Place 1 guerrilla in each of two spaces.
        self.env.board.spaces[s1].pieces[2] = 1  # M26 UG
        self.env.board.spaces[s2].pieces[5] = 1  # DR UG

        before_total = int(
            self.env.board.spaces[s1].pieces[2]
            + self.env.board.spaces[s1].pieces[3]
            + self.env.board.spaces[s1].pieces[5]
            + self.env.board.spaces[s1].pieces[6]
            + self.env.board.spaces[s1].pieces[8]
            + self.env.board.spaces[s1].pieces[9]
            + self.env.board.spaces[s2].pieces[2]
            + self.env.board.spaces[s2].pieces[3]
            + self.env.board.spaces[s2].pieces[5]
            + self.env.board.spaces[s2].pieces[6]
            + self.env.board.spaces[s2].pieces[8]
            + self.env.board.spaces[s2].pieces[9]
        )

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Pick 1
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_empty = self.env._target_space_action_base + s_empty
        self.assertEqual(self.env.legal_actions[pick_empty], 0)

        pick1 = self.env._target_space_action_base + s1
        self.assertEqual(self.env.legal_actions[pick1], 1)
        self.env.step(pick1)

        # Pick 2
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick2 = self.env._target_space_action_base + s2
        self.assertEqual(self.env.legal_actions[pick2], 1)
        self.env.step(pick2)

        after_total = int(
            self.env.board.spaces[s1].pieces[2]
            + self.env.board.spaces[s1].pieces[3]
            + self.env.board.spaces[s1].pieces[5]
            + self.env.board.spaces[s1].pieces[6]
            + self.env.board.spaces[s1].pieces[8]
            + self.env.board.spaces[s1].pieces[9]
            + self.env.board.spaces[s2].pieces[2]
            + self.env.board.spaces[s2].pieces[3]
            + self.env.board.spaces[s2].pieces[5]
            + self.env.board.spaces[s2].pieces[6]
            + self.env.board.spaces[s2].pieces[8]
            + self.env.board.spaces[s2].pieces[9]
        )

        self.assertEqual(after_total, before_total - 2)


if __name__ == "__main__":
    unittest.main()
