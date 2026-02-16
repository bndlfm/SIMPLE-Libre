import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    OP_MARCH_M26,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard13ElChe(unittest.TestCase):
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

    def test_el_che_shaded_is_blank_and_masked_out(self):
        d = EVENT_DECK_DATA[13]
        self.env.current_card = Card(13, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 1
        for p in self.env.players:
            p.eligible = True
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

        choose_shaded = self.env._event_side_base + EVENT_SHADED
        self.assertEqual(int(self.env.legal_actions[choose_shaded]), 0)

    def test_el_che_unshaded_grants_capability_and_first_m26_march_group_stays_underground(self):
        d = EVENT_DECK_DATA[13]
        self.env.current_card = Card(13, d["name"], d["order"], d["unshaded"], d["shaded"])

        # Play the event as M26 so it grants the capability.
        self.env.current_player_num = 1
        for p in self.env.players:
            p.eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertIn("ElChe_Unshaded", self.env.capabilities)

        # Setup: Place 2 M26 Underground guerrillas in Pinar (0), and March into an EC/City.
        self.env.board.spaces[0].pieces[2] = 2
        self.env.players[1].resources = 10

        dest_space = 1  # Cigar EC (type 4): normally activates guerrillas that enter

        # Start an M26 March op directly.
        self.env.current_player_num = 1
        self.env.phase = PHASE_CHOOSE_OP_ACTION

        action = self.env._ops_action_base + (OP_MARCH_M26 * self.env.num_spaces) + dest_space
        self.assertEqual(int(self.env.legal_actions[action]), 1)
        self.env.step(action)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_src = self.env._target_space_action_base + 0
        self.assertEqual(int(self.env.legal_actions[pick_src]), 1)
        self.env.step(pick_src)

        # First moved group should stay Underground due to El Che capability.
        self.assertEqual(int(self.env.board.spaces[dest_space].pieces[2]), 1)
        self.assertEqual(int(self.env.board.spaces[dest_space].pieces[3]), 0)


if __name__ == "__main__":
    unittest.main()
