import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    EVENT_SHADED,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    OP_KIDNAP_M26,
)


class TestEventRulesUpdates(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.closed_casinos = 0
            sp.cash[:] = 0
            sp.cash_holders[:] = 0
            sp.update_control()

    def _start_event(self, card_id, shaded):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_echeverria_shaded_closest_and_resources(self):
        d = EVENT_DECK_DATA[27]
        self.env.current_card = Card(27, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        self.env.players[2].resources = 10
        self.env.board.spaces[3].pieces[5] = 1  # Havana DR Underground
        self.env.board.spaces[3].pieces[6] = 1  # Havana DR Active
        self.env.board.spaces[0].pieces[5] = 1  # Another DR piece elsewhere

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        dist = self.env._shortest_space_distances(3)
        min_dist = min(
            dist.get(sp.id, 999)
            for sp in self.env.board.spaces
            if int(sp.pieces[5] + sp.pieces[6] + sp.pieces[7]) > 0
        )
        for sp in self.env.board.spaces:
            action = self.env._target_space_action_base + sp.id
            if int(sp.pieces[5] + sp.pieces[6] + sp.pieces[7]) > 0 and dist.get(sp.id, 999) == min_dist:
                self.assertEqual(self.env.legal_actions[action], 1)
            else:
                self.assertEqual(self.env.legal_actions[action], 0)

        pick_havana = self.env._target_space_action_base + 3
        self.env.step(pick_havana)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        remove_active = self.env._event_option_action_base + 1
        self.assertEqual(self.env.legal_actions[remove_active], 1)
        self.env.step(remove_active)

        self.assertEqual(int(self.env.players[2].resources), 7)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(pick_havana)
        remove_underground = self.env._event_option_action_base + 0
        if self.env.phase == PHASE_CHOOSE_EVENT_OPTION:
            self.env.step(remove_underground)

        havana = self.env.board.spaces[3]
        self.assertEqual(int(havana.pieces[5] + havana.pieces[6] + havana.pieces[7]), 0)

    def test_defections_unshaded_choice_flow(self):
        d = EVENT_DECK_DATA[35]
        self.env.current_card = Card(35, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 1  # M26
        self.env.players[1].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 3
        sp = self.env.board.spaces[target]
        sp.pieces[2] = 1  # M26 Underground
        sp.pieces[0] = 1  # Govt Troop
        sp.pieces[1] = 1  # Govt Police
        sp.pieces[5] = 1  # DR Underground (extra enemy faction)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_space = self.env._target_space_action_base + target
        self.assertEqual(self.env.legal_actions[pick_space], 1)
        self.env.step(pick_space)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        choose_govt = self.env._target_faction_action_base + 0
        self.assertEqual(self.env.legal_actions[choose_govt], 1)
        self.env.step(choose_govt)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        remove_troop = self.env._event_option_action_base + 0
        self.assertEqual(self.env.legal_actions[remove_troop], 1)
        self.env.step(remove_troop)
        self.assertEqual(int(sp.pieces[0]), 0)
        self.assertEqual(int(sp.pieces[2]), 2)

        remove_police = self.env._event_option_action_base + 1
        if self.env.phase == PHASE_CHOOSE_EVENT_OPTION:
            self.env.step(remove_police)
        self.assertEqual(int(sp.pieces[1]), 0)
        self.assertEqual(int(sp.pieces[2]), 3)

    def test_defections_unshaded_does_not_allow_removing_enemy_base_or_casino(self):
        d = EVENT_DECK_DATA[35]
        self.env.current_card = Card(35, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 1  # M26
        self.env.players[1].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 3
        sp = self.env.board.spaces[target]
        sp.pieces[2] = 1  # M26 Underground (our presence)
        sp.pieces[7] = 1  # DR Base (enemy base)
        sp.pieces[10] = 1  # Syndicate Casino (enemy casino)
        sp.pieces[5] = 1  # DR Underground (enemy guerrilla so event is legal)
        sp.pieces[8] = 1  # Syndicate Underground (ensures multiple enemy factions with removable pieces)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_space = self.env._target_space_action_base + target
        self.env.step(pick_space)

        # Multiple enemies -> choose enemy faction.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        choose_dr = self.env._target_faction_action_base + 2
        self.assertEqual(self.env.legal_actions[choose_dr], 1)
        self.env.step(choose_dr)

        # Only guerrillas should be removable; base should remain.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.assertEqual(int(sp.pieces[7]), 1)

    def test_defections_unshaded_govt_replacement_can_choose_troop_or_police(self):
        d = EVENT_DECK_DATA[35]
        self.env.current_card = Card(35, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 0  # Govt
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 3
        sp = self.env.board.spaces[target]
        sp.pieces[0] = 1  # Govt Troop (our presence)
        sp.pieces[2] = 2  # M26 Underground (enemy cubes/guerrillas)
        self.env.players[0].available_forces[0] = 1  # Troop available
        self.env.players[0].available_forces[1] = 1  # Police available

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        self.env.step(self.env._target_space_action_base + target)

        # Single enemy faction -> should go straight to piece choice.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        remove_enemy = self.env._event_option_action_base + 0
        self.assertEqual(self.env.legal_actions[remove_enemy], 1)
        self.env.step(remove_enemy)

        # After removing one enemy, Govt must choose which cube to place back (Troop vs Police).
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        choose_troop = self.env._event_option_action_base + 0
        choose_police = self.env._event_option_action_base + 1
        self.assertEqual(int(self.env.legal_actions[choose_troop]), 1)
        self.assertEqual(int(self.env.legal_actions[choose_police]), 1)

        # Choose Police for the replacement.
        self.env.step(choose_police)
        self.assertEqual(int(sp.pieces[1]), 1)

    @unittest.skip("Covered by tests/cubalibre/test_card_12_brac.py")
    def test_brac_unshaded_choice_flow(self):
        d = EVENT_DECK_DATA[12]
        self.env.current_card = Card(12, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 4
        sp = self.env.board.spaces[target]
        sp.pieces[2] = 1  # M26 Underground
        sp.pieces[6] = 1  # DR Active
        sp.pieces[5] = 1  # DR Underground

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_space = self.env._target_space_action_base + target
        self.env.step(pick_space)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        choose_dr = self.env._target_faction_action_base + 2
        self.assertEqual(self.env.legal_actions[choose_dr], 1)
        self.env.step(choose_dr)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        remove_active = self.env._event_option_action_base + 1
        self.assertEqual(self.env.legal_actions[remove_active], 1)
        self.env.step(remove_active)
        self.assertEqual(int(sp.pieces[6]), 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

    def test_pact_of_caracas_blocks_kidnap(self):
        self.env.current_player_num = 1  # M26
        self.env.players[1].eligible = True
        self.env.same_player_control = False
        self.env.capabilities.add("PactOfCaracas_Unshaded")
        self.env.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

        s_id = 3
        sp = self.env.board.spaces[s_id]
        sp.pieces[2] = 1  # M26 Underground

        kidnap_action = self.env._ops_action_base + (OP_KIDNAP_M26 * self.env.num_spaces) + s_id
        self.assertEqual(self.env.legal_actions[kidnap_action], 0)

    def test_menoyo_unshaded_choice(self):
        d = EVENT_DECK_DATA[36]
        self.env.current_card = Card(36, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 2  # DR
        self.env.players[2].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 5  # Las Villas
        sp = self.env.board.spaces[target]
        sp.pieces[0] = 1  # Govt Troop
        sp.pieces[1] = 1  # Govt Police
        self.env.players[2].available_forces[0] = 2

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_space = self.env._target_space_action_base + target
        self.env.step(pick_space)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        remove_troop = self.env._event_option_action_base + 0
        self.assertEqual(self.env.legal_actions[remove_troop], 1)
        self.env.step(remove_troop)

        self.assertEqual(int(sp.pieces[0]), 0)
        self.assertEqual(int(sp.pieces[5]), 2)

    def test_menoyo_shaded_remove_or_replace(self):
        d = EVENT_DECK_DATA[36]
        self.env.current_card = Card(36, d["name"], d["order"], d["unshaded"], d["shaded"])
        self.env.current_player_num = 2  # DR
        self.env.players[2].eligible = True
        self.env.phase = 0

        target = 5  # Las Villas
        sp = self.env.board.spaces[target]
        sp.pieces[5] = 1  # DR Underground
        sp.pieces[6] = 1  # DR Active
        self.env.players[1].available_forces[0] = 1  # M26 available

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_space = self.env._target_space_action_base + target
        self.env.step(pick_space)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        remove_underground = self.env._event_option_action_base + 0
        self.assertEqual(self.env.legal_actions[remove_underground], 1)
        self.env.step(remove_underground)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        choose_m26 = self.env._target_faction_action_base + 1
        self.assertEqual(self.env.legal_actions[choose_m26], 1)
        self.env.step(choose_m26)

        self.assertEqual(int(sp.pieces[5]), 0)
        self.assertEqual(int(sp.pieces[2]), 1)


if __name__ == "__main__":
    unittest.main()
