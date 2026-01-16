import unittest

from app.environments.cubalibre.envs.constants import (
    US_ALLIANCE_EMBARGOED,
    US_ALLIANCE_FIRM,
    US_ALLIANCE_RELUCTANT,
)
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    OP_AIR_STRIKE,
    OP_TRAIN_FORCE,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
)


class TestCampaignTrackOpCostsAndLegality(unittest.TestCase):
    def _find_train_force_action(self, env: CubaLibreEnv) -> int:
        for space_id in range(env.num_spaces):
            action = env._ops_action_base + OP_TRAIN_FORCE * env.num_spaces + space_id
            if env.legal_actions[action] == 1:
                return action
        self.fail("No legal Train Force action found for Govt.")

    def _run_train_with_alliance(self, alliance_level: int) -> int:
        env = CubaLibreEnv(verbose=False, manual=False)
        env.reset(seed=123)
        env.set_us_alliance(alliance_level)
        env.phase = PHASE_CHOOSE_OP_ACTION
        env.current_player_num = 0
        env.players[0].eligible = True
        env.players[0].resources = 10
        env.players[0].available_forces[0] = 10
        action = self._find_train_force_action(env)
        env.step(action)
        return env.players[0].resources

    def test_govt_op_cost_tracks_us_alliance(self):
        remaining = self._run_train_with_alliance(US_ALLIANCE_FIRM)
        self.assertEqual(remaining, 8)

        remaining = self._run_train_with_alliance(US_ALLIANCE_RELUCTANT)
        self.assertEqual(remaining, 7)

        remaining = self._run_train_with_alliance(US_ALLIANCE_EMBARGOED)
        self.assertEqual(remaining, 6)

    def test_airstrike_illegal_when_embargoed(self):
        env = CubaLibreEnv(verbose=False, manual=False)
        env.reset(seed=123)
        env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
        env.current_player_num = 0
        env.players[0].eligible = True
        env.players[0].resources = 10

        target_space = None
        for sp in env.board.spaces:
            if sp.type in [1, 3]:
                sp.pieces[3] = 1  # active M26 guerrilla
                target_space = sp.id
                break
        self.assertIsNotNone(target_space)

        airstrike = env._ops_action_base + OP_AIR_STRIKE * env.num_spaces + target_space

        env.set_us_alliance(US_ALLIANCE_FIRM)
        self.assertEqual(env.legal_actions[airstrike], 1)

        env.set_us_alliance(US_ALLIANCE_EMBARGOED)
        self.assertEqual(env.legal_actions[airstrike], 0)


if __name__ == "__main__":
    unittest.main()
