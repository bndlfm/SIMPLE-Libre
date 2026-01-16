import unittest

from app.environments.cubalibre.envs.classes import PropagandaCard
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    MAIN_OPS,
    MAIN_PASS,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_PROPAGANDA_REDEPLOY_MENU,
)


class TestPropagandaRedeployAndFinal(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        # Clean the board
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.alignment = 0
            sp.support_active = False
            sp.terror = 0
            sp.sabotage = False
            sp.update_control()

    def test_redeploy_moves_police_and_troops_to_valid_destinations(self):
        # Put Govt Troops on an Econ Center and on a Province with no Govt base.
        cigar = self.env.board.spaces[1]  # EC
        pinar = self.env.board.spaces[0]  # Province
        havana = self.env.board.spaces[3]  # City (default fallback)

        for sp in self.env.board.spaces:
            sp.alignment = 1
            sp.support_active = True

        cigar.pieces[0] = 1
        pinar.pieces[0] = 2
        pinar.pieces[1] = 1

        # Ensure Havana is Govt-controlled (so it's a valid troop destination).
        havana.pieces[0] = 1
        havana.pieces[1] = 1
        havana.update_control()
        self.assertEqual(havana.controlled_by, 1)

        self.env.players[0].resources = 0
        self.env.aid = 0
        self.env.players[1].resources = 0

        self.env._propaganda_start_redeploy()
        self.assertEqual(self.env.phase, PHASE_PROPAGANDA_REDEPLOY_MENU)

        mask = self.env.legal_actions
        self.assertEqual(mask[self.env._main_action_base + MAIN_PASS], 0)
        self.assertEqual(mask[self.env._main_action_base + MAIN_EVENT], 1)
        self.assertEqual(mask[self.env._main_action_base + MAIN_OPS], 1)

        # Optional police redeploy.
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + pinar.id)
        self.env.step(self.env._target_space_action_base + havana.id)

        self.assertEqual(pinar.pieces[1], 0)
        self.assertEqual(havana.pieces[1], 2)

        # Back to menu.
        self.env.step(self.env._main_action_base + MAIN_PASS)
        self.assertEqual(self.env.phase, PHASE_PROPAGANDA_REDEPLOY_MENU)

        # Mandatory troop redeploys.
        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.env.step(self.env._target_space_action_base + pinar.id)
        self.env.step(self.env._target_space_action_base + havana.id)
        self.env.step(self.env._target_space_action_base + pinar.id)
        self.env.step(self.env._target_space_action_base + havana.id)
        self.env.step(self.env._target_space_action_base + cigar.id)
        self.env.step(self.env._target_space_action_base + havana.id)

        # Police should be moved off the origin and end up in some EC or Govt-controlled destination.
        total_police = sum(int(sp.pieces[1]) for sp in self.env.board.spaces)
        # We started with 2 total police: 1 in Pinar and 1 in Havana.
        self.assertEqual(total_police, 2)
        self.assertTrue(any((sp.type == 4 or sp.controlled_by == 1) and int(sp.pieces[1]) > 0 for sp in self.env.board.spaces))

        # Troops should be moved off ECs and provinces without Govt bases to a Govt-controlled city/base.
        self.assertEqual(cigar.pieces[0], 0)
        self.assertEqual(pinar.pieces[0], 0)
        self.assertGreaterEqual(havana.pieces[0], 1 + 1 + 2)

    def test_resolve_propaganda_does_not_auto_redeploy_optional_troops(self):
        cigar = self.env.board.spaces[1]  # EC (mandatory)
        pinar = self.env.board.spaces[0]  # Province (mandatory)
        havana = self.env.board.spaces[3]  # City (valid destination)
        santiago = self.env.board.spaces[12]  # City (optional source)

        cigar.pieces[0] = 1
        pinar.pieces[0] = 1
        santiago.pieces[0] = 2
        havana.pieces[0] = 1
        havana.pieces[1] = 1
        havana.update_control()
        self.assertEqual(havana.controlled_by, 1)

        self.env.players[0].resources = 0
        self.env.aid = 0
        self.env.propaganda_cards_played = 1

        self.env.resolve_propaganda()

        self.assertEqual(int(cigar.pieces[0]), 0)
        self.assertEqual(int(pinar.pieces[0]), 0)
        self.assertEqual(int(santiago.pieces[0]), 2)

    def test_redeploy_optional_troops_allows_moving_other_troops(self):
        # 6.4.3: Govt may move any other Troops to Govt-Controlled Cities or Bases.
        # Setup: no mandatory troop redeploy sources, but one optional troop source.
        santiago = self.env.board.spaces[12]  # City (optional source)
        havana = self.env.board.spaces[3]  # City (destination)

        # Make Havana Govt-controlled so it's a valid troop destination.
        havana.pieces[0] = 2
        havana.pieces[1] = 1
        havana.update_control()
        self.assertEqual(havana.controlled_by, 1)

        # Optional source: Troops in a City (not EC, not Province w/out Govt base).
        santiago.pieces[0] = 2
        santiago.update_control()

        self.env._propaganda_start_redeploy()
        self.assertEqual(self.env.phase, PHASE_PROPAGANDA_REDEPLOY_MENU)

        # Choose troop redeploy (no mandatory sources => optional step).
        self.env.step(self.env._main_action_base + MAIN_OPS)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # Pick optional troop source.
        self.env.step(self.env._target_space_action_base + santiago.id)
        # Pick destination.
        self.env.step(self.env._target_space_action_base + havana.id)

        # One troop moved.
        self.assertEqual(int(santiago.pieces[0]), 1)
        self.assertEqual(int(havana.pieces[0]), 3)

        # Optional redeploy can continue or be stopped; PASS returns to menu.
        self.env.step(self.env._main_action_base + MAIN_PASS)
        self.assertEqual(self.env.phase, PHASE_PROPAGANDA_REDEPLOY_MENU)

    def test_final_propaganda_ends_game_on_draw_next_card(self):
        # Force deck to draw a propaganda card.
        self.env.deck.cards = [PropagandaCard(999)]
        self.env.propaganda_cards_played = 3

        # Set some state that would normally be cleared by Reset.
        self.env.board.spaces[1].terror = 1
        self.env.board.spaces[10].sabotage = True
        self.env.capabilities.add("Raul_Shaded")

        ok = self.env.draw_next_card()
        self.assertFalse(ok)
        self.assertEqual(self.env.propaganda_cards_played, 4)

        # Complete final Propaganda choice flow (Expat Backing pass).
        if self.env.phase == PHASE_CHOOSE_TARGET_SPACE:
            self.env.step(self.env._main_action_base + 0)

        self.assertTrue(self.env.deck_empty)

        # Final propaganda omits Redeploy and Reset (6.3.5): markers/capabilities should remain.
        self.assertEqual(self.env.board.spaces[1].terror, 1)
        self.assertTrue(self.env.board.spaces[10].sabotage)
        self.assertIn("Raul_Shaded", self.env.capabilities)

    def test_final_propaganda_resolve_skips_resources_redeploy_and_reset(self):
        # Final Propaganda round should skip resources, redeploy, and reset.
        self.env.propaganda_cards_played = 4

        self.env.board.spaces[1].terror = 1
        self.env.board.spaces[10].sabotage = True
        self.env.capabilities.add("Raul_Shaded")

        self.env.players[0].resources = 0
        self.env.aid = 5

        result = self.env.resolve_propaganda()

        # No winner expected, but ensure it returns and does not clear/reset state.
        self.assertFalse(result)
        self.assertEqual(self.env.players[0].resources, 0)
        self.assertEqual(self.env.board.spaces[1].terror, 1)
        self.assertTrue(self.env.board.spaces[10].sabotage)
        self.assertIn("Raul_Shaded", self.env.capabilities)
        self.assertNotEqual(self.env.phase, PHASE_PROPAGANDA_REDEPLOY_MENU)

    def test_final_propaganda_victory_phase_ends_immediately(self):
        # 2.4.1: If there is victory in the 4th Propaganda card's Victory Phase, the game ends immediately.
        self.env.deck.cards = [PropagandaCard(999)]
        self.env.propaganda_cards_played = 3

        for sp in self.env.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                sp.alignment = 1
                sp.support_active = True
                sp.update_control()

        ok = self.env.draw_next_card()

        self.assertFalse(ok)
        self.assertTrue(self.env.deck_empty)
        self.assertFalse(self.env._propaganda_in_progress)
        self.assertEqual(self.env.propaganda_cards_played, 4)
        self.assertNotEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

    def test_final_propaganda_no_victory_runs_support_phase_only(self):
        # 2.4.1 / 6.3.5: If no victory in the final Propaganda Victory Phase, execute Support Phase only.
        self.env.propaganda_cards_played = 4

        # Set a Support Phase target: Govt Civic Action should spend resources to clear terror.
        havana = self.env.board.spaces[3]
        havana.pieces[0] = 1
        havana.pieces[1] = 1
        havana.terror = 1
        havana.update_control()

        self.env.players[0].resources = 4
        self.env.aid = 10

        self.env.resolve_propaganda()

        # Support phase applied: terror removed and resources spent, but resources phase skipped.
        self.assertEqual(havana.terror, 0)
        self.assertEqual(self.env.players[0].resources, 0)
        # Total Support <= 18 triggers US Alliance test (6.3.1), reducing Aid by 10.
        self.assertEqual(self.env.aid, 0)

    def test_final_propaganda_no_victory_skips_redeploy_and_reset(self):
        # 2.4.1 / 6.3.5: final Propaganda without victory skips Redeploy/Reset.
        self.env.propaganda_cards_played = 4

        cigar = self.env.board.spaces[1]  # EC (would be mandatory redeploy source)
        pinar = self.env.board.spaces[0]  # Province (would be mandatory redeploy source)

        cigar.pieces[0] = 1
        pinar.pieces[0] = 2
        cigar.update_control()
        pinar.update_control()

        self.env.players[0].resources = 0
        self.env.aid = 0

        self.env.resolve_propaganda()

        # Troops should remain because Redeploy/Reset are skipped.
        self.assertEqual(int(cigar.pieces[0]), 1)
        self.assertEqual(int(pinar.pieces[0]), 2)

    def test_final_propaganda_victory_margin_formula_setup(self):
        # 7.3: After final Propaganda without a victory check win, compare victory margins.
        self.env.propaganda_cards_played = 4

        # Government: Total Support - 18.
        havana = self.env.board.spaces[3]
        havana.alignment = 1
        havana.support_active = True
        havana.update_control()

        # 26July: Total Opposition + Bases - 15.
        santiago = self.env.board.spaces[12]
        santiago.alignment = 2
        santiago.support_active = True
        santiago.update_control()
        santiago.pieces[4] = 3

        # Directorio: DR-controlled population + DR bases - 9.
        dr_space = self.env.board.spaces[5]
        dr_space.pieces[5] = 3
        dr_space.pieces[7] = 2
        dr_space.update_control()

        # Syndicate: min(open casinos - 7, resources - 30).
        casino = self.env.board.spaces[1]
        casino.pieces[10] = 5
        casino.update_control()
        self.env.players[3].resources = 40

        self.env._refresh_campaign_tracks()

        govt_margin = self.env.total_support_track - 18
        m26_margin = self.env.opposition_plus_bases_track - 15
        dr_margin = self.env.dr_pop_plus_bases_track - 9
        syn_margin = min(self.env.open_casinos_track - 7, self.env.players[3].resources - 30)

        self.assertEqual(govt_margin, havana.population * 2 - 18)
        self.assertEqual(m26_margin, santiago.population * 2 + 3 - 15)
        self.assertEqual(dr_margin, dr_space.population + 2 - 9)
        self.assertEqual(syn_margin, min(5 - 7, 40 - 30))

    def test_final_propaganda_sets_victory_results(self):
        # Final Propaganda without victory should store margins and ranking results.
        self.env.propaganda_cards_played = 4

        self.env.players[0].resources = 0
        self.env.aid = 0

        result = self.env.resolve_propaganda()

        self.assertFalse(result)
        self.assertIsNotNone(self.env.final_victory_margins_result)
        self.assertIsNotNone(self.env.final_victory_ranking_result)
        self.assertEqual(len(self.env.final_victory_margins_result), 4)
        self.assertEqual(len(self.env.final_victory_ranking_result), 4)


if __name__ == "__main__":
    unittest.main()
