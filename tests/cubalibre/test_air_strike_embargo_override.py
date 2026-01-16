import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    OP_AIR_STRIKE,
)


class TestAirStrikeEmbargoOverride(unittest.TestCase):
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
    def test_air_strike_allowed_under_embargo_with_guantanamo_shaded(self):
        self.env.capabilities.add("Guantanamo_Shaded")
        self.env.set_us_alliance(2)  # Embargoed
        self.env.current_player_num = 0  # Govt
        self.env.players[0].resources = 5
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

        sierra = 11  # Mountain
        self.env.board.spaces[sierra].pieces[3] = 1  # Active M26 guerrilla

        action = self.env._ops_action_base + OP_AIR_STRIKE * self.env.num_spaces + sierra
        self.assertEqual(self.env.legal_actions[action], 1)


if __name__ == "__main__":
    unittest.main()
