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


class TestCard7Election(unittest.TestCase):
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

    def test_card_7_election_unshaded_places_one_guerrilla_in_each_city_with_faction_choices(self):
        d = EVENT_DECK_DATA[7]
        self.env.current_card = Card(7, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 1  # M26 (arbitrary)
        self.env.players[1].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        # Ensure sufficient available guerrillas.
        self.env.players[1].available_forces[0] = 20
        self.env.players[2].available_forces[0] = 20
        self.env.players[3].available_forces[0] = 20

        cities = [s.id for s in self.env.board.spaces if s.type == 0]
        self.assertGreater(len(cities), 0)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        # Choose a faction for each city, verifying the piece appears in that city.
        for i, city_id in enumerate(cities):
            self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

            # Cycle factions: M26 -> DR -> Syndicate -> ...
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

    def test_card_7_election_shaded_sets_city_neutral_and_aid_plus_10(self):
        d = EVENT_DECK_DATA[7]
        self.env.current_card = Card(7, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_EVENT_SIDE
        self.env.card_action_slot = 0

        self.env.aid = 5

        target_city = 12
        self.env.board.spaces[target_city].type = 0
        self.env.board.spaces[target_city].alignment = 2
        self.env.board.spaces[target_city].support_active = True

        self.env.step(self.env._event_side_base + EVENT_SHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_city = self.env._target_space_action_base + target_city
        self.assertEqual(int(self.env.legal_actions[pick_city]), 1)
        self.env.step(pick_city)

        sp = self.env.board.spaces[target_city]
        self.assertEqual(int(sp.alignment), 0)
        self.assertFalse(bool(sp.support_active))
        self.assertEqual(int(self.env.aid), 15)


if __name__ == "__main__":
    unittest.main()
