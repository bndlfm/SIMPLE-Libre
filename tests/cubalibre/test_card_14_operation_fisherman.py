import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_MAIN,
)


class TestCard14OperationFisherman(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        d = EVENT_DECK_DATA[14]
        self.env.current_card = Card(14, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        for p in self.env.players:
            p.eligible = True

    def test_operation_fisherman_unshaded_places_m26_base_and_guerrilla_in_pinar(self):
        pinar = 0
        sp = self.env.board.spaces[pinar]

        before_bases = int(sp.pieces[4])
        before_guerrillas = int(sp.pieces[2] + sp.pieces[3])

        self.env.players[1].available_bases = 10
        self.env.players[1].available_forces[0] = 10

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        after_bases = int(sp.pieces[4])
        after_guerrillas = int(sp.pieces[2] + sp.pieces[3])

        self.assertEqual(after_bases, before_bases + 1)
        self.assertEqual(after_guerrillas, before_guerrillas + 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_operation_fisherman_shaded_shifts_pinar_two_levels_toward_active_support(self):
        pinar = 0
        sp = self.env.board.spaces[pinar]

        # From Neutral, 2 steps toward support => Active Support.
        sp.alignment = 0
        sp.support_active = False

        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.current_player_num = 0

        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(int(sp.alignment), 1)
        self.assertEqual(bool(sp.support_active), True)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
