import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_EVENT_OPTION,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard21Fangio(unittest.TestCase):
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

    def _set_card(self, card_id):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def _start_event(self, shaded, acting_player=0):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_shifts_city_toward_active_opposition_two_levels_if_m26_present(self):
        # Card 21 (Fangio, Un): Shift a City 1 toward Active Opposition (2 if M26 piece).
        self._set_card(21)

        s = 12  # Santiago de Cuba (City)
        self.env.board.spaces[s].pieces[2] = 1  # M26 piece present
        self.env.board.spaces[s].alignment = 1  # Support
        self.env.board.spaces[s].support_active = True

        self._start_event(shaded=False, acting_player=0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + s)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

        self.assertEqual(int(self.env.board.spaces[s].alignment), 0)

    def test_shaded_cash_owner_choices_are_limited_to_factions_with_cube_or_guerrilla(self):
        # Card 21 (Fangio, Sh): Cash owner choice should be masked to only factions with a cube/guerrilla in space.
        self._set_card(21)

        s1 = 3  # Havana
        s2 = 5  # Las Villas

        # Make them qualify as "spaces with any Casinos"
        self.env.board.spaces[s1].closed_casinos = 1
        self.env.board.spaces[s2].pieces[10] = 1

        # Only Govt has a cube in s2 (no other cubes/guerrillas)
        self.env.board.spaces[s2].pieces[0] = 1

        self._start_event(shaded=True, acting_player=0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + s1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 0)  # open casino

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        self.env.step(self.env._target_space_action_base + s2)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)
        self.env.step(self.env._event_option_action_base + 1)  # place cash

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        choose_govt = self.env._target_faction_action_base + 0
        choose_m26 = self.env._target_faction_action_base + 1
        choose_dr = self.env._target_faction_action_base + 2
        choose_syn = self.env._target_faction_action_base + 3

        self.assertEqual(int(self.env.legal_actions[choose_govt]), 1)
        self.assertEqual(int(self.env.legal_actions[choose_m26]), 0)
        self.assertEqual(int(self.env.legal_actions[choose_dr]), 0)
        self.assertEqual(int(self.env.legal_actions[choose_syn]), 0)


if __name__ == "__main__":
    unittest.main()
