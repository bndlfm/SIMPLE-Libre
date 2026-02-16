import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_SHADED,
    EVENT_UNSHADED,
    MAIN_EVENT,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard20TheTwelve(unittest.TestCase):
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

    def _start_event(self, shaded, acting_player=1):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_free_march_then_full_free_rally_at_destination(self):
        # Card 20 (The Twelve, Un): A Faction free Marches then free Rallies at a March destination.
        self._set_card(20)

        # M26 guerrillas within 1 of Oriente (9): Sierra Maestra (11) and Sugar Cane EC (10)
        self.env.board.spaces[11].pieces[2] = 1
        self.env.board.spaces[10].pieces[2] = 1

        # Limit available guerrillas so Rally expectation is stable.
        self.env.players[1].available_forces[0] = 2

        self._start_event(shaded=False, acting_player=1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        # Choose M26
        self.env.step(self.env._target_faction_action_base + 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # Choose Oriente as destination
        self.env.step(self.env._target_space_action_base + 9)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

        # Expect March moved 2 guerrillas into Oriente, then Rally placed 2 more.
        self.assertEqual(int(self.env.board.spaces[9].pieces[2]), 4)
        self.assertEqual(int(self.env.board.spaces[11].pieces[2]), 0)
        self.assertEqual(int(self.env.board.spaces[10].pieces[2]), 0)

    def test_shaded_removes_half_rounded_up_from_space_with_most_guerrillas(self):
        # Card 20 (The Twelve, Sh): Remove 1/2 rounded up of any Guerrillas from the space with the most Guerrillas.
        self._set_card(20)

        # Pinar (0) total=4, Matanzas (4) total=3
        self.env.board.spaces[0].pieces[2] = 3
        self.env.board.spaces[0].pieces[5] = 1
        self.env.board.spaces[4].pieces[8] = 3

        m26_avail_before = int(self.env.players[1].available_forces[0])
        dr_avail_before = int(self.env.players[2].available_forces[0])
        syn_avail_before = int(self.env.players[3].available_forces[0])

        self._start_event(shaded=True, acting_player=0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        # Only Pinar should be targetable (max total guerrillas).
        self.assertEqual(int(self.env.legal_actions[self.env._target_space_action_base + 0]), 1)
        self.assertEqual(int(self.env.legal_actions[self.env._target_space_action_base + 4]), 0)

        self.env.step(self.env._target_space_action_base + 0)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

        remaining = int(self.env.board.spaces[0].pieces[2] + self.env.board.spaces[0].pieces[3]
                        + self.env.board.spaces[0].pieces[5] + self.env.board.spaces[0].pieces[6]
                        + self.env.board.spaces[0].pieces[8] + self.env.board.spaces[0].pieces[9])
        self.assertEqual(remaining, 2)

        gained = (
            (int(self.env.players[1].available_forces[0]) - m26_avail_before)
            + (int(self.env.players[2].available_forces[0]) - dr_avail_before)
            + (int(self.env.players[3].available_forces[0]) - syn_avail_before)
        )
        self.assertEqual(gained, 2)


if __name__ == "__main__":
    unittest.main()
