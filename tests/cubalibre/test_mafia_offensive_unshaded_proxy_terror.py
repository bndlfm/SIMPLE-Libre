import unittest
from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    OP_TERROR_M26,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    PHASE_CHOOSE_MAIN,
)

class TestMafiaOffensiveUnshadedProxyTerror(unittest.TestCase):
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

    def test_mafia_offensive_uses_syndicate_proxy_for_terror(self):
        d = EVENT_DECK_DATA[43]
        self.env.current_card = Card(43, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 3  # SYNDICATE
        self.env.players[3].eligible = True
        self.env.phase = 0

        havana_id = 1
        self.env.board.spaces[havana_id].pieces[8] = 1  # Syndicate Underground
        self.env.board.spaces[havana_id].alignment = 1

        syndicate_res = int(self.env.players[3].resources)
        m26_res = int(self.env.players[1].resources)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        self.env.step(self.env._target_faction_action_base + 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_LIMITED_OP_ACTION)

        action = self.env._limited_ops_action_base + OP_TERROR_M26 * 13 + havana_id
        self.env.step(action)

        sp = self.env.board.spaces[havana_id]
        self.assertEqual(int(sp.pieces[8]), 0)
        self.assertEqual(int(sp.pieces[9]), 1)
        self.assertEqual(int(sp.terror), 1)
        self.assertEqual(int(self.env.players[3].resources), syndicate_res)
        self.assertEqual(int(self.env.players[1].resources), m26_res)
        self.assertIsNone(self.env._pending_mafia_offensive)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

if __name__ == "__main__":
    unittest.main()
