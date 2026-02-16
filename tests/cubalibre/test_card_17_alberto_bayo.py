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
)


class TestCard17AlbertoBayo(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.update_control()

        for p in self.env.players:
            p.eligible = True

    def _set_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def _start_event(self, shaded: bool, acting_player: int = 0):
        self.env.current_player_num = acting_player
        self.env.players[acting_player].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_unshaded_dr_free_rallies_in_each_dr_base_space(self):
        # Card 17 unshaded: choose DR, then DR free Rallies in each space where it has a Base.
        self._set_card(17)

        # Put DR Bases in two spaces.
        s1 = 5
        s2 = 9
        self.env.board.spaces[s1].pieces[7] = 1
        self.env.board.spaces[s2].pieces[7] = 1

        # Force at least one flip opportunity: an Active DR guerrilla becomes Underground.
        self.env.board.spaces[s2].pieces[6] = 1

        # Force Rally to take the flip path (no available guerrillas to place).
        self.env.players[2].available_forces[0] = 0

        self._start_event(shaded=False, acting_player=1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        # Choose DR.
        self.env.step(self.env._target_faction_action_base + 2)

        # Active should have flipped to Underground.
        self.assertEqual(int(self.env.board.spaces[s2].pieces[6]), 0)
        self.assertGreaterEqual(int(self.env.board.spaces[s2].pieces[5]), 1)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_shaded_activates_all_m26_guerrillas_and_makes_m26_ineligible_through_next_card(self):
        # Card 17 shaded: All M26 guerrillas Active; M26 ineligible through next card.
        self._set_card(17)

        s = 11
        self.env.board.spaces[s].pieces[2] = 2
        self.env.board.spaces[s].pieces[3] = 1

        self._start_event(shaded=True, acting_player=0)

        self.assertEqual(int(self.env.board.spaces[s].pieces[2]), 0)
        self.assertEqual(int(self.env.board.spaces[s].pieces[3]), 3)
        self.assertIn(1, self.env.ineligible_through_next_card)
        self.assertFalse(self.env.players[1].eligible)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
