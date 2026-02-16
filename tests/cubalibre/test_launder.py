import unittest

from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_OPS,
    MAIN_PASS,
    PHASE_CHOOSE_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    OP_RALLY_M26,
    OP_RALLY_SYN,
    OP_CONSTRUCT_SYN,
)


class TestLaunder(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.sabotage = False
            sp.closed_casinos = 0
            sp.update_control()

        for p in self.env.players:
            p.eligible = True
            p.resources = 0

    def test_launder_other_faction_cash_enables_free_limited_op(self):
        # Acting faction (M26) will pay for an Op but skip SA, enabling Launder.
        self.env.current_player_num = 1
        self.env.phase = 0
        self.env.card_action_slot = 0
        self.env.players[1].resources = 2

        # Provide M26 a simple Rally target.
        target = 0

        # Put a Syndicate-owned Cash marker in Havana so Syndicate can be the provider.
        cash_space = 3
        sp_cash = self.env.board.spaces[cash_space]
        sp_cash.pieces[8] = 1
        self.env._add_cash_marker(sp_cash, 3)

        # Perform Ops.
        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        rally_action = self.env._ops_action_base + (OP_RALLY_M26 * self.env.num_spaces) + target
        self.assertEqual(int(self.env.legal_actions[rally_action]), 1)
        self.env.step(rally_action)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)

        # Skip SA -> Launder should trigger (paid op, no SA).
        self.env.step(self.env._main_action_base + MAIN_PASS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        # Choose provider faction: Syndicate (3).
        self.env.step(self.env._target_faction_action_base + 3)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # Choose space containing that cash.
        self.env.step(self.env._target_space_action_base + cash_space)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_LIMITED_OP_ACTION)

        # Make acting faction unable to pay normally, to prove it's free.
        self.env.players[1].resources = 0

        # Free LimOp: Rally should be available even with 0 resources.
        lim_rally = self.env._limited_ops_action_base + (OP_RALLY_M26 * self.env.num_spaces) + target
        self.assertEqual(int(self.env.legal_actions[lim_rally]), 1)

        self.env.step(lim_rally)
        self.assertEqual(self.env.phase, 0)

    def test_launder_once_per_card(self):
        self.env.current_player_num = 1
        self.env.phase = 0
        self.env.card_action_slot = 0
        self.env.players[1].resources = 2

        cash_space = 3
        sp_cash = self.env.board.spaces[cash_space]
        sp_cash.pieces[8] = 1
        self.env._add_cash_marker(sp_cash, 3)

        self.env.step(self.env._main_action_base + MAIN_OPS)
        rally_action = self.env._ops_action_base + (OP_RALLY_M26 * self.env.num_spaces) + 0
        self.env.step(rally_action)
        self.env.step(self.env._main_action_base + MAIN_PASS)
        self.env.step(self.env._target_faction_action_base + 3)
        self.env.step(self.env._target_space_action_base + cash_space)

        lim_rally = self.env._limited_ops_action_base + (OP_RALLY_M26 * self.env.num_spaces) + 0
        self.env.step(lim_rally)

        # Try to launder again: perform another paid op and skip SA.
        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.players[1].resources = 2
        self.env.phase = 0

        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.env.step(rally_action)
        self.env.step(self.env._main_action_base + MAIN_PASS)

        # Launder should not trigger a second time this card.
        self.assertNotEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

    def test_launder_free_limited_op_cannot_be_construct(self):
        # Launder (2.3.6) explicitly forbids Construct from being free.
        # Set Syndicate as the acting faction, then confirm Construct is not legal during the free LimOp.
        self.env.current_player_num = 3  # Syndicate
        self.env.phase = 0
        self.env.card_action_slot = 0
        self.env.players[3].resources = 2

        # Give Syndicate a simple paid Op: Rally.
        rally_target = 0
        self.env.board.spaces[rally_target].pieces[8] = 1  # Syndicate Underground
        self.env.board.spaces[rally_target].update_control()

        # Provide any faction-owned cash to launder (Syndicate itself is fine).
        cash_space = 3
        sp_cash = self.env.board.spaces[cash_space]
        sp_cash.pieces[8] = 1
        self.env._add_cash_marker(sp_cash, 3)

        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_OP_ACTION)

        rally_action = self.env._ops_action_base + (OP_RALLY_SYN * self.env.num_spaces) + rally_target
        self.assertEqual(int(self.env.legal_actions[rally_action]), 1)
        self.env.step(rally_action)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)

        # Skip SA -> Launder prompt.
        self.env.step(self.env._main_action_base + MAIN_PASS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        # Choose provider faction: Syndicate (3).
        self.env.step(self.env._target_faction_action_base + 3)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + cash_space)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_LIMITED_OP_ACTION)

        # During Launder's free LimOp, Construct must not be legal.
        lim_construct = self.env._limited_ops_action_base + (OP_CONSTRUCT_SYN * self.env.num_spaces) + rally_target
        self.assertEqual(int(self.env.legal_actions[lim_construct]), 0)

    def test_paid_limited_op_allows_syndicate_construct(self):
        # Limited Operation (2.3.5) is any Operation in 1 space (no SA).
        # Construct is only restricted from being *free* (2.3.6 / 3.3.5), not from being a LimOp.
        self.env.current_player_num = 3  # Syndicate
        self.env.players[3].eligible = True
        self.env.players[3].resources = 5
        self.env._launder_free = False
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION

        target = 0
        sp = self.env.board.spaces[target]
        sp.pieces[8] = 1  # Syndicate Underground (enables Syndicate ops)
        sp.update_control()

        self.env.players[3].available_bases = 1

        lim_construct = self.env._limited_ops_action_base + (OP_CONSTRUCT_SYN * self.env.num_spaces) + target
        self.assertEqual(int(self.env.legal_actions[lim_construct]), 1)


if __name__ == "__main__":
    unittest.main()
