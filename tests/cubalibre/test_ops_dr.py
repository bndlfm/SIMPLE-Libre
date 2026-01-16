import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv, PHASE_CHOOSE_MAIN, MAIN_OPS, MAIN_PASS, PHASE_CHOOSE_SPECIAL_ACTIVITY


class TestDROps(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=3)
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.update_control()
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 2
        self.env.players[2].eligible = True
        self.env.players[2].resources = 10

    def _do_ops_action(self, op, space_id, sa_op=None, sa_space_id=None):
        # These unit tests exercise single ops resolutions; force a slot-0 context so MAIN_OPS is legal.
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 2
        self.env.players[self.env.current_player_num].eligible = True
        enter_ops = self.env._main_action_base + MAIN_OPS
        self.assertEqual(self.env.legal_actions[enter_ops], 1)
        self.env.step(enter_ops)
        a = self.env._ops_action_base + op * self.env.num_spaces + space_id
        self.assertEqual(self.env.legal_actions[a], 1)
        obs, r, term, trunc, info = self.env.step(a)

        if self.env.phase == PHASE_CHOOSE_SPECIAL_ACTIVITY:
            if sa_op is None:
                skip = self.env._main_action_base + MAIN_PASS
                self.assertEqual(self.env.legal_actions[skip], 1)
                obs, r, term, trunc, info = self.env.step(skip)
            else:
                sa = self.env._ops_action_base + sa_op * self.env.num_spaces + sa_space_id
                self.assertEqual(self.env.legal_actions[sa], 1)
                obs, r, term, trunc, info = self.env.step(sa)
        return obs

    def test_assassinate_places_terror_and_kills_one_govt(self):
        havana = 3
        # govt pieces present
        self.env.board.spaces[havana].pieces[0] = 2
        self.env.board.spaces[havana].pieces[1] = 2
        # DR active present
        self.env.board.add_piece(havana, 2, 1)

        start_g = self.env.board.spaces[havana].pieces[0] + self.env.board.spaces[havana].pieces[1]
        # Do a normal Op first (Rally), then choose the Assassinate special activity.
        self._do_ops_action(op=11, space_id=havana, sa_op=17, sa_space_id=havana)

        end_g = self.env.board.spaces[havana].pieces[0] + self.env.board.spaces[havana].pieces[1]
        self.assertEqual(end_g, start_g - 1)
        self.assertEqual(self.env.board.spaces[havana].terror, 1)


if __name__ == "__main__":
    unittest.main()
