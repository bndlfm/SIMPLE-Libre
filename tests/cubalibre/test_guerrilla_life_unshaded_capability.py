import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_OP_ACTION,
    OP_RALLY_M26,
)


@unittest.skip("Covered by tests/cubalibre/test_card_30_the_guerrilla_life.py")
class TestGuerrillaLifeUnshadedCapability(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash_holders[:] = 0
            sp.refresh_cash_counts()
            sp.update_control()

    def test_event_adds_capability(self):
        d = EVENT_DECK_DATA[30]
        self.env.current_card = Card(30, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 1  # M26
        self.env.players[1].eligible = True
        self.env.phase = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertIn("GuerrillaLife_Unshaded", self.env.capabilities)

    def test_m26_rally_flips_actives_even_when_placing(self):
        self.env.capabilities.add("GuerrillaLife_Unshaded")

        space_id = 0  # Pinar Del Rio (Province)
        sp = self.env.board.spaces[space_id]
        sp.pieces[3] = 1  # M26 Active
        self.assertTrue(self.env._add_cash_marker(sp, 1, preferred_idx=3))

        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.players[1].resources = 10
        self.env.players[1].available_forces[0] = 3
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.card_action_slot = 0

        action = self.env._ops_action_base + OP_RALLY_M26 * self.env.num_spaces + space_id
        self.assertEqual(self.env.legal_actions[action], 1)

        self.env.step(action)

        self.assertEqual(int(sp.pieces[3]), 0)
        self.assertGreaterEqual(int(sp.pieces[2]), 2)
        self.assertEqual(int(sp.cash_holders[2]), 1)


if __name__ == "__main__":
    unittest.main()
