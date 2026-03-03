import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_EVENT_OPTION,
    MAIN_EVENT,
    EVENT_UNSHADED,
    EVENT_SHADED
)

class TestEdgeCasesMultiStepEvents(unittest.TestCase):
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

    def test_manifesto_unshaded_multi_faction_loop(self):
        self.env.board.spaces[0].pieces[0] = 1 # Govt
        self.env.board.spaces[1].pieces[2] = 1 # M26
        self.env.board.spaces[2].pieces[5] = 1 # DR
        self.env.board.spaces[3].pieces[8] = 1 # Syndicate

        self.env.current_player_num = 0
        self.env.phase = PHASE_CHOOSE_MAIN

        from app.environments.cubalibre.envs.classes import Card
        self.env.current_card = Card(19, "Sierra Maestra Manifesto", [1, 2, 3, 0], False, False)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_event_target["f_idx"], 1)

        self.env.step(self.env._target_space_action_base + 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + 1)
        self.env.step(self.env._event_option_action_base + 0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_event_target["f_idx"], 2)

        self.env.step(self.env._target_space_action_base + 2)
        self.env.step(self.env._event_option_action_base + 0)
        self.env.step(self.env._target_space_action_base + 2)
        self.env.step(self.env._event_option_action_base + 0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_event_target["f_idx"], 3)

        self.env.step(self.env._target_space_action_base + 3)
        self.env.step(self.env._target_space_action_base + 3)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.assertEqual(self.env._pending_event_target["f_idx"], 0)

        self.env.step(self.env._target_space_action_base + 0)
        self.env.step(self.env._event_option_action_base + 0)
        self.env.step(self.env._target_space_action_base + 0)
        self.env.step(self.env._event_option_action_base + 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

        self.assertEqual(self.env.board.spaces[1].pieces[2], 3)
        self.assertEqual(self.env.board.spaces[2].pieces[5], 3)
        self.assertEqual(self.env.board.spaces[3].pieces[8], 3)
        self.assertEqual(self.env.board.spaces[0].pieces[0], 2)
        self.assertEqual(self.env.board.spaces[0].pieces[1], 1)

    def test_defections_unshaded_enemy_choice(self):
        s_id = 4 # Matanzas
        sp = self.env.board.spaces[s_id]

        sp.pieces[0] = 1 # Govt
        sp.pieces[3] = 1 # M26
        sp.pieces[6] = 1 # DR

        self.env.current_player_num = 0
        self.env.phase = PHASE_CHOOSE_MAIN
        from app.environments.cubalibre.envs.classes import Card
        self.env.current_card = Card(35, "Defections", [0, 1, 2, 3], False, False)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + s_id)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        legal = self.env.legal_actions
        self.assertEqual(legal[self.env._target_faction_action_base + 1], 1)
        self.assertEqual(legal[self.env._target_faction_action_base + 2], 1)
        self.assertEqual(legal[self.env._target_faction_action_base + 3], 0)

        self.env.step(self.env._target_faction_action_base + 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertEqual(sp.pieces[3], 0)
        self.assertEqual(sp.pieces[0], 2)

if __name__ == '__main__':
    unittest.main()
