import unittest
import numpy as np
from app.environments.cubalibre.envs.env import CubaLibreEnv

class TestAmbushRules(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv()
        self.env.reset()

        self.OP_AMBUSH_M26 = 15

        # Clear board
        for sp in self.env.board.spaces:
            sp.pieces = np.zeros(11, dtype=int)
            sp.govt_bases = 0

        # Give M26 an underground guerrilla and resources
        self.env.players[1].resources = 10 # M26 is index 1
        self.sp = self.env.board.spaces[0]
        self.sp.pieces[2] = 1 # M26 Underground Guerrilla
        self.sp.pieces[0] = 1 # Govt Troop

        # Force M26 turn
        self.env.deck = ["US Speaking Tour"]
        self.env.current_player_num = 1
        self.env.phase = 4 # PHASE_CHOOSE_SPECIAL_ACTIVITY

    def test_ambush_requires_underground_guerrilla(self):
        # Change M26 to active
        self.sp.pieces[2] = 0
        self.sp.pieces[3] = 1 # Active

        masks = self.env.action_masks()
        sa_idx = self.env._ops_action_base + self.OP_AMBUSH_M26 * 13 + 0
        self.assertEqual(masks[sa_idx], False, "Ambush requires Underground Guerrilla")

    def test_ambush_removes_one_govt_piece_and_places_underground(self):
        sa_idx = self.env._ops_action_base + self.OP_AMBUSH_M26 * 13 + 0
        self.env.step(sa_idx)

        # If it paused for target selection, supply target selection
        if self.env.phase == 6: # PHASE_CHOOSE_TARGET_FACTION
            self.env.step(self.env._target_faction_action_base + 0) # Govt

        if self.env.phase == 8: # PHASE_CHOOSE_TARGET_PIECE
             masks = self.env.action_masks()
             self.env.step(np.argmax(masks)) # Should pick Troop (0)

        # Should have removed 1 Troop
        self.assertEqual(self.sp.pieces[0], 0, "Govt Troop should be removed")

        # M26 guerrilla should flip to Active
        self.assertEqual(self.sp.pieces[2], 1, "There should be 1 Underground Guerrilla (the reward one)")
        self.assertEqual(self.sp.pieces[3], 1, "The ambushing Guerrilla should have flipped to active")

    def test_ambush_against_base_no_reward(self):
        # Setup Govt Base instead of Troop
        self.sp.pieces[0] = 0
        self.sp.govt_bases = 1

        sa_idx = self.env._ops_action_base + self.OP_AMBUSH_M26 * 13 + 0
        self.env.step(sa_idx)

        if self.env.phase == 6:
            self.env.step(self.env._target_faction_action_base + 0)

        if self.env.phase == 8:
             masks = self.env.action_masks()
             self.env.step(np.argmax(masks)) # Should pick Base (11)

        # Should have removed 1 Base
        self.assertEqual(self.sp.govt_bases, 0, "Govt Base should be removed")

        # M26 guerrilla should flip to Active, but NO reward!
        self.assertEqual(self.sp.pieces[2], 0, "Should NOT get a free underground guerrilla for removing a Base")
        self.assertEqual(self.sp.pieces[3], 1, "The ambushing Guerrilla should have flipped to active")

    def test_ambush_can_target_other_factions(self):
        # Remove Govt, add DR
        self.sp.pieces[0] = 0
        self.sp.pieces[5] = 1 # DR Underground Guerrilla

        # Need to make sure the mask allows DR
        masks = self.env.action_masks()
        sa_idx = self.env._ops_action_base + self.OP_AMBUSH_M26 * 13 + 0
        self.assertTrue(masks[sa_idx], "Ambush should be able to target DR")

        self.env.step(sa_idx)

        if self.env.phase == 6: # PHASE_CHOOSE_TARGET_FACTION
            self.env.step(self.env._target_faction_action_base + 2) # DR

        if self.env.phase == 8: # PHASE_CHOOSE_TARGET_PIECE
             masks = self.env.action_masks()
             self.env.step(np.argmax(masks))

        # Should remove DR Guerrilla
        self.assertEqual(self.sp.pieces[5], 0, "DR Guerrilla should be removed")
        self.assertEqual(self.sp.pieces[2], 0, "M26 should NOT gain a Guerrilla because target was not Govt")
        self.assertEqual(self.sp.pieces[3], 1, "The ambushing Guerrilla should flip to active")

if __name__ == '__main__':
    unittest.main()
