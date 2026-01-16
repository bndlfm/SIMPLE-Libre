import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_MAIN, MAIN_OPS, MAIN_PASS, PHASE_CHOOSE_SPECIAL_ACTIVITY


class TestM26Ops(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=2)
        # make deterministic-ish
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.update_control()
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.players[1].resources = 10

    def _do_ops_action(self, op, space_id):
        # These unit tests exercise single ops resolutions; force a slot-0 context so MAIN_OPS is legal.
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 1
        self.env.players[self.env.current_player_num].eligible = True
        # go to ops phase
        enter_ops = self.env._main_action_base + MAIN_OPS
        self.assertEqual(self.env.legal_actions[enter_ops], 1)
        self.env.step(enter_ops)
        a = self.env._ops_action_base + op * self.env.num_spaces + space_id
        self.assertEqual(self.env.legal_actions[a], 1)
        obs, r, term, trunc, info = self.env.step(a)

        # Ops may offer an optional Special Activity; these tests skip it.
        if self.env.phase == PHASE_CHOOSE_SPECIAL_ACTIVITY:
            skip = self.env._main_action_base + MAIN_PASS
            self.assertEqual(self.env.legal_actions[skip], 1)
            obs, r, term, trunc, info = self.env.step(skip)
        return obs

    def test_rally_place_then_flip(self):
        sierra = 11
        # have an active guerrilla to later flip
        self.env.board.add_piece(sierra, 1, 1)

        # first rally should place at least 1 underground if supply available
        start_u = self.env.board.spaces[sierra].pieces[2]
        self._do_ops_action(op=7, space_id=sierra)  # OP_RALLY_M26
        self.assertGreaterEqual(self.env.board.spaces[sierra].pieces[2], start_u)

        # exhaust supply -> rally should flip active to underground
        self.env.players[1].available_forces[0] = 0
        start_a = self.env.board.spaces[sierra].pieces[3]
        self._do_ops_action(op=7, space_id=sierra)
        self.assertLessEqual(self.env.board.spaces[sierra].pieces[3], start_a)
        self.assertGreaterEqual(self.env.board.spaces[sierra].pieces[2], 1)

    def test_terror_places_marker_and_shifts_alignment(self):
        lv = 5
        self.env.board.spaces[lv].alignment = 1
        self.env.board.add_piece(lv, 1, 0)

        self._do_ops_action(op=10, space_id=lv)  # OP_TERROR_M26

        self.assertEqual(self.env.board.spaces[lv].terror, 1)
        self.assertEqual(self.env.board.spaces[lv].alignment, 0)


if __name__ == "__main__":
    unittest.main()
