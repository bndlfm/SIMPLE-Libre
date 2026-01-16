import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    OP_KIDNAP_M26,
)


class TestGuantanamoUnshadedKidnapLocation(unittest.TestCase):
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

    @unittest.skip("Covered by tests/cubalibre/test_card_2_guantanamo_bay.py")
    def test_kidnap_allowed_in_sierra_maestra_with_capability(self):
        self.env.capabilities.add("Guantanamo_Unshaded")
        self.env.current_player_num = 1  # M26
        self.env.players[1].resources = 5
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

        sierra = 11  # Sierra Maestra
        self.env.board.spaces[sierra].pieces[2] = 1

        action = self.env._ops_action_base + OP_KIDNAP_M26 * self.env.num_spaces + sierra
        self.assertEqual(self.env.legal_actions[action], 1)


if __name__ == "__main__":
    unittest.main()
