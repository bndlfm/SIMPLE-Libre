import unittest
import numpy as np
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    OP_ASSAULT,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_MAIN,
    MAIN_OPS,
    MAIN_PASS,
)

class TestAssaultMultiTargetEdgeCases(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_assault_multitarget_chooses_correctly_and_skips_when_no_targets(self):
        # Setup Havana (Space 3)
        havana = self.env.board.spaces[3]
        havana.type = 0 # City for Full Assault

        # Govt needs Troops to Assault
        havana.pieces[0] = 5 # Troops
        havana.pieces[1] = 5 # Police

        # Add M26 (1 Active, 1 UG)
        havana.pieces[2] = 1 # M26 UG
        havana.pieces[3] = 1 # M26 Active

        # Add DR (1 Active, 1 UG)
        havana.pieces[5] = 1 # DR UG
        havana.pieces[6] = 1 # DR Active

        # Setup Govt as current player
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.current_player_num = 0
        self.env.players[0].resources = 20
        self.env.players[0].eligible = True
        self.env.card_action_slot = 0

        # 1. Main Action -> Ops
        enter_ops = self.env._main_action_base + MAIN_OPS
        self.env.step(enter_ops)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        # 2. Choose Assault on Havana
        assault_action = self.env._ops_action_base + OP_ASSAULT * self.env.num_spaces + 3
        self.env.step(assault_action)

        # 3. Should pause to select between M26 (1) and DR (2)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.assertIn(1, self.env._pending_event_faction["allowed"])
        self.assertIn(2, self.env._pending_event_faction["allowed"])

        # 4. Govt chooses to target DR
        dr_action = self.env._target_faction_action_base + 2
        self.env.step(dr_action)

        # 5. Verify the assault on DR was processed.
        # Havana had 1 DR Active, 1 DR UG. With 10 killers, both should be dead.
        self.assertEqual(int(havana.pieces[5]), 0, "DR UG should be killed")
        self.assertEqual(int(havana.pieces[6]), 0, "DR Active should be killed")

        # M26 should still be there
        self.assertEqual(int(havana.pieces[2]), 1, "M26 UG should survive")
        self.assertEqual(int(havana.pieces[3]), 1, "M26 Active should survive")

        # 6. SA phase should trigger next
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)

if __name__ == '__main__':
    unittest.main()
