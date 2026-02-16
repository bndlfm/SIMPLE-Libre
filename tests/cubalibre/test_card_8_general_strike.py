import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard8GeneralStrike(unittest.TestCase):
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
            if hasattr(sp, "cash"):
                sp.cash[:] = 0
            if hasattr(sp, "cash_holders"):
                sp.cash_holders[:] = 0
            if hasattr(sp, "cash_owner_by_holder"):
                sp.cash_owner_by_holder[:] = -1
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

    def test_card_8_general_strike_unshaded_shifts_cities_toward_neutral_and_places_guerrillas(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 1
        self.env.players[1].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        # Ensure adequate available guerrillas.
        self.env.players[1].available_forces[0] = 20
        self.env.players[2].available_forces[0] = 20
        self.env.players[3].available_forces[0] = 20

        cities = [s.id for s in self.env.board.spaces if s.type == 0]
        self.assertGreater(len(cities), 0)

        # Seed some non-neutral alignment to verify shifting.
        first_city = int(cities[0])
        sp0 = self.env.board.spaces[first_city]
        sp0.alignment = 1
        sp0.support_active = True

        last_city = int(cities[-1])
        spl = self.env.board.spaces[last_city]
        spl.alignment = 2
        spl.support_active = False

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # After event starts, all cities should already be shifted 1 step toward Neutral.
        self.assertEqual(int(sp0.alignment), 1)
        self.assertFalse(bool(sp0.support_active))
        self.assertEqual(int(spl.alignment), 0)

        # Choose faction for each city and verify placement.
        for i, city_id in enumerate(cities):
            self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
            pick_faction = [1, 2, 3][i % 3]
            self.env.step(self.env._target_faction_action_base + pick_faction)

            sp = self.env.board.spaces[int(city_id)]
            if pick_faction == 1:
                self.assertEqual(int(sp.pieces[2]), 1)
            elif pick_faction == 2:
                self.assertEqual(int(sp.pieces[5]), 1)
            else:
                self.assertEqual(int(sp.pieces[8]), 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_card_8_general_strike_shaded_opens_any_closed_casino_anywhere(self):
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

        target_city = 8
        self.env.board.spaces[target_city].type = 0

        # Put underground guerrillas of multiple factions.
        self.env.board.spaces[target_city].pieces[2] = 1  # M26 UG
        self.env.board.spaces[target_city].pieces[5] = 1  # DR UG
        self.env.board.spaces[target_city].pieces[8] = 1  # SYN UG

        # Put the closed casino somewhere else, to verify "open any 1".
        open_space = 3
        self.env.board.spaces[open_space].closed_casinos = 1

        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_city = self.env._target_space_action_base + target_city
        self.assertEqual(int(self.env.legal_actions[pick_city]), 1)
        self.env.step(pick_city)

        sp = self.env.board.spaces[target_city]

        # City set to Active Support.
        self.assertEqual(int(sp.alignment), 1)
        self.assertTrue(bool(sp.support_active))

        # All guerrillas activated.
        self.assertEqual(int(sp.pieces[2]), 0)
        self.assertEqual(int(sp.pieces[5]), 0)
        self.assertEqual(int(sp.pieces[8]), 0)
        self.assertEqual(int(sp.pieces[3]), 1)
        self.assertEqual(int(sp.pieces[6]), 1)
        self.assertEqual(int(sp.pieces[9]), 1)

        # Now choose where to open the closed casino.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_open = self.env._target_space_action_base + open_space
        self.assertEqual(int(self.env.legal_actions[pick_open]), 1)
        self.env.step(pick_open)

        sp_open = self.env.board.spaces[open_space]
        self.assertEqual(int(sp_open.closed_casinos), 0)
        self.assertEqual(int(sp_open.pieces[10]), 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
