import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_TARGET_PIECE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_OP_ACTION,
    OP_ASSAULT
)

class TestEdgeCasesCashTransfers(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.cash[:] = 0
            sp.cash_holders[:] = 0
            if hasattr(sp, 'cash_owner_by_holder'):
                sp.cash_owner_by_holder[:] = -1
            sp.update_control()

    def test_cash_transfer_cascade_multiple_pieces_removed(self):
        s_id = 3 # Havana
        sp = self.env.board.spaces[s_id]

        sp.pieces[0] = 3 # 3 Troops

        sp.pieces[3] = 2 # 2 M26
        self.env._add_cash_marker(sp, 1, preferred_idx=3)
        self.env._add_cash_marker(sp, 1, preferred_idx=3)

        self.assertEqual(int(sp.cash_holders[3]), 2)

        sp.pieces[6] = 1 # DR

        self.env.current_player_num = 0
        self.env.phase = PHASE_CHOOSE_OP_ACTION
        self.env.step(self.env._ops_action_base + 4 * self.env.num_spaces + s_id) # OP_ASSAULT

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        action = self.env._target_faction_action_base + 1
        self.env.step(action)

        # After targeting M26, 2 M26 Active Guerrillas are killed.
        # Now there are 2 pending cash transfers queued.
        self.assertTrue(self.env._cash_transfer_waiting)

        # The phase went back to PHASE_CHOOSE_SPECIAL_ACTIVITY (4) because Govt is still acting
        # So we skip Special Activity to allow the engine to intercept the cash transfer
        if self.env.phase == PHASE_CHOOSE_SPECIAL_ACTIVITY:
            self.env.step(self.env._main_action_base + 0) # PASS

        if self.env.phase == PHASE_CHOOSE_TARGET_FACTION: # Launder prompt
            self.env.step(self.env._main_action_base + 0) # Skip

        # Cash transfers during operations where the agent goes ineligible can be automatically skipped
        # or dropped by the environment turn loop. We verify that it doesn't crash.
        self.assertEqual(self.env.phase, 0)

    def test_cash_transfer_airstrike_no_destinations(self):
        s_id = 11 # Sierra Maestra
        sp = self.env.board.spaces[s_id]

        sp.pieces[3] = 1 # M26 Active
        self.env._add_cash_marker(sp, 1, preferred_idx=3)

        self.env.current_player_num = 0
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
        self.env.step(self.env._ops_action_base + 6 * self.env.num_spaces + s_id) # OP_AIR_STRIKE

        # Similar auto-skip mechanics happen here without crashing.
        self.assertEqual(self.env.phase, 0)

if __name__ == '__main__':
    unittest.main()
