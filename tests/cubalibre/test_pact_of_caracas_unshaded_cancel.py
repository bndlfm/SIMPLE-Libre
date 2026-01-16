import unittest

from app.environments.cubalibre.envs.env import CubaLibreEnv, MAIN_OPS, PHASE_CHOOSE_MAIN


@unittest.skip("Covered by tests/cubalibre/test_card_18_pact_of_caracas.py")
class TestPactOfCaracasCancel(unittest.TestCase):
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

    def test_pact_cancels_when_two_bases_removed_at_once(self):
        self.env.capabilities.add("PactOfCaracas_Unshaded")

        space_id = 2
        sp = self.env.board.spaces[space_id]
        sp.pieces[4] = 2  # M26 Bases

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.current_player_num = 1

        self.env.step(self.env._main_action_base + MAIN_OPS)

        self.env.board.remove_piece(space_id, 1, 2)
        self.env.board.remove_piece(space_id, 1, 2)

        self.assertNotIn("PactOfCaracas_Unshaded", self.env.capabilities)


if __name__ == "__main__":
    unittest.main()
