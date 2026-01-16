import unittest
import numpy as np

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_OP_ACTION,
)


class TestCubaLibrePhaseObservation(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)

    def test_observation_shape_and_header_fields(self):
        obs, info = self.env.reset(seed=123)
        self.assertEqual(obs.shape, (self.env.obs_size,))
        self.assertEqual(self.env.observation_space.shape, (self.env.obs_size,))

        # Header fields
        self.assertEqual(int(obs[0]), PHASE_CHOOSE_MAIN)
        self.assertEqual(int(obs[1]), int(self.env.current_player_num))
        self.assertEqual(int(obs[2]), int(self.env.factions_acted_this_card))
        self.assertEqual(int(obs[3]), int(self.env.us_alliance))
        self.assertEqual(int(obs[4]), int(self.env.current_card.id))
        self.assertIn(int(obs[5]), (-1, 0, 1))

        # Aid track
        self.assertEqual(int(obs[9]), int(self.env.aid))

        # Derived victory markers
        self.assertEqual(int(obs[10]), int(self.env.total_support_value()))
        self.assertEqual(int(obs[11]), int(self.env.opposition_plus_bases_value()))
        self.assertEqual(int(obs[12]), int(self.env.dr_pop_plus_bases_value()))
        self.assertEqual(int(obs[13]), int(self.env.open_casinos_value()))

        spaces_flat = obs[self.env._obs_header_size:]
        self.assertEqual(spaces_flat.shape[0], self.env.num_spaces * self.env.space_feature_size)
        self.assertTrue(np.isfinite(spaces_flat).all())

    def test_phase_transitions_update_observation(self):
        obs, info = self.env.reset(seed=123)
        # Force a simple card that doesn't have targeting (e.g., Card 2)
        from app.environments.cubalibre.envs.classes import Card
        self.env.current_card = Card(2, "Guantanamo Bay", [0, 1, 2, 3], "Unshaded", "Shaded")

        # Choose EVENT
        obs, reward, terminated, truncated, info = self.env.step(1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_SIDE)
        self.assertEqual(int(obs[0]), PHASE_CHOOSE_EVENT_SIDE)
        self.assertEqual(int(obs[5]), 0)  # pending main = event

        # Choose side (pick first legal)
        mask = self.env.legal_actions
        legal = [i for i, x in enumerate(mask) if x == 1]
        self.assertTrue(len(legal) > 0)
        obs, reward, terminated, truncated, info = self.env.step(legal[0])

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertEqual(int(obs[0]), PHASE_CHOOSE_MAIN)

    def test_legal_actions_respects_phase(self):
        obs, info = self.env.reset(seed=123)

        mask = self.env.legal_actions
        legal = [i for i, x in enumerate(mask) if x == 1]
        self.assertEqual(len(legal), 3)

        # Move to ops phase
        ops_action = self.env._main_action_base + 2
        self.assertEqual(mask[ops_action], 1)
        obs, reward, terminated, truncated, info = self.env.step(ops_action)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        mask = self.env.legal_actions
        legal = [i for i, x in enumerate(mask) if x == 1]
        self.assertTrue(len(legal) > 0)

    def test_observation_header_tracks_and_resources(self):
        obs, info = self.env.reset(seed=123)
        self.env.set_aid(22)
        self.env.players[self.env.current_player_num].resources = 17

        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 1
                sp.support_active = True
            sp.pieces[10] = 0
            sp.update_control()
        self.env.board.spaces[0].pieces[10] = 2
        self.env.board.spaces[0].update_control()

        obs = self.env.observation

        self.assertEqual(int(obs[6]), 17)
        self.assertEqual(int(obs[9]), 22)
        self.assertGreater(int(obs[10]), 0)
        self.assertEqual(int(obs[13]), 2)


if __name__ == "__main__":
    unittest.main()
