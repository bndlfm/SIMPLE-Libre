import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    OP_MARCH_M26,
    OP_ATTACK_M26,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_MAIN,
)


class TestMafiaOffensiveUnshadedProxyOps(unittest.TestCase):
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

    def _start_mafia_offensive_for_m26(self):
        d = EVENT_DECK_DATA[43]
        self.env.current_card = Card(43, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 3  # SYNDICATE
        self.env.players[3].eligible = True
        self.env.phase = 0

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        self.env.step(self.env._target_faction_action_base + 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_LIMITED_OP_ACTION)

    def test_mafia_offensive_proxy_march_moves_syndicate_piece(self):
        self._start_mafia_offensive_for_m26()

        dest_id = next(sp.id for sp in self.env.board.spaces if sp.type == 0 and sp.adj_ids)
        src_id = self.env.board.spaces[dest_id].adj_ids[0]
        if src_id == dest_id:
            src_id = (dest_id + 1) % self.env.num_spaces
            self.env.board.spaces[dest_id].adj_ids = [src_id]

        self.env.board.spaces[src_id].pieces[8] = 1  # Syndicate Underground

        march_to_dest = self.env._limited_ops_action_base + OP_MARCH_M26 * self.env.num_spaces + dest_id
        self.assertEqual(self.env.legal_actions[march_to_dest], 1)

        self.env.step(march_to_dest)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_src = self.env._target_space_action_base + src_id
        self.assertEqual(self.env.legal_actions[pick_src], 1)

        self.env.step(pick_src)

        self.assertEqual(int(self.env.board.spaces[src_id].pieces[8] + self.env.board.spaces[src_id].pieces[9]), 0)
        if self.env.board.spaces[dest_id].type in [0, 4]:
            self.assertEqual(int(self.env.board.spaces[dest_id].pieces[9]), 1)
        else:
            self.assertEqual(int(self.env.board.spaces[dest_id].pieces[8]), 1)
        if self.env.phase == PHASE_CHOOSE_TARGET_SPACE:
            self.env.step(self.env._main_action_base + 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertIsNone(self.env._pending_mafia_offensive)

    def test_mafia_offensive_proxy_march_allows_only_one_syndicate_piece_total(self):
        self._start_mafia_offensive_for_m26()

        # Build a deterministic adjacency setup for March:
        # - One source with only Syndicate guerrilla (will be used as the 1 borrowed piece)
        # - One source with only Syndicate guerrilla (should become illegal after first use)
        # - One source with M26 guerrilla (should remain legal)
        dest_id = 3  # Havana (City)
        src_syn_used = 2
        src_syn_remaining = 4
        src_m26 = 0
        self.env.board.spaces[dest_id].adj_ids = [src_syn_used, src_syn_remaining, src_m26]

        self.env.board.spaces[src_syn_used].pieces[8] = 1  # Syndicate Underground
        self.env.board.spaces[src_syn_remaining].pieces[8] = 1  # Syndicate Underground
        self.env.board.spaces[src_m26].pieces[2] = 1  # M26 Underground

        march_to_dest = self.env._limited_ops_action_base + OP_MARCH_M26 * self.env.num_spaces + dest_id
        self.assertEqual(self.env.legal_actions[march_to_dest], 1)
        self.env.step(march_to_dest)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # First, use the borrowed Syndicate piece.
        pick_src_syn = self.env._target_space_action_base + src_syn_used
        self.assertEqual(self.env.legal_actions[pick_src_syn], 1)
        self.env.step(pick_src_syn)

        # March should continue because an M26 source remains. But other Syndicate-only sources should be blocked.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_src_syn_remaining = self.env._target_space_action_base + src_syn_remaining
        pick_src_m26 = self.env._target_space_action_base + src_m26
        self.assertEqual(self.env.legal_actions[pick_src_syn_remaining], 0)
        self.assertEqual(self.env.legal_actions[pick_src_m26], 1)

        # Finish by moving the real M26 guerrilla.
        self.env.step(pick_src_m26)
        if self.env.phase == PHASE_CHOOSE_TARGET_SPACE:
            self.env.step(self.env._main_action_base + 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertIsNone(self.env._pending_mafia_offensive)

    def test_mafia_offensive_proxy_attack_uses_syndicate_piece(self):
        self._start_mafia_offensive_for_m26()

        target_id = next(sp.id for sp in self.env.board.spaces if sp.type == 0)
        sp = self.env.board.spaces[target_id]
        sp.pieces[8] = 1  # Syndicate Underground
        sp.pieces[1] = 2  # Police

        self.env._roll_die = lambda: 1

        attack_action = self.env._limited_ops_action_base + OP_ATTACK_M26 * self.env.num_spaces + target_id
        self.assertEqual(self.env.legal_actions[attack_action], 1)

        self.env.step(attack_action)

        self.assertEqual(int(sp.pieces[8]), 0)
        self.assertEqual(int(sp.pieces[9]), 1)
        self.assertEqual(int(sp.pieces[1]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertIsNone(self.env._pending_mafia_offensive)


if __name__ == "__main__":
    unittest.main()
