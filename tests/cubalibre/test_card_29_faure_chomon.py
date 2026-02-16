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


class TestCard29FaureChomon(unittest.TestCase):
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

    def _start_event(self, shaded):
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0
        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + (EVENT_SHADED if shaded else EVENT_UNSHADED))

    def test_chomon_un_places_base_and_two_guerrillas_in_las_villas_m26(self):
        # Card 29 (Fauré Chomón, Un): DR or M26 places a Base and 2 Guerrillas in Las Villas.
        self._set_card(29)

        self.env.players[1].available_bases = 1
        self.env.players[1].available_forces[0] = 10

        self._start_event(shaded=False)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        self.env.step(self.env._target_faction_action_base + 1)  # Choose M26

        sp = self.env.board.spaces[5]  # Las Villas
        self.assertEqual(int(sp.pieces[4]), 1)  # M26 Base
        self.assertEqual(int(sp.pieces[2]), 2)  # 2 M26 Underground Guerrillas
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_chomon_un_places_base_and_two_guerrillas_in_las_villas_dr(self):
        # Card 29 (Fauré Chomón, Un): DR or M26 places a Base and 2 Guerrillas in Las Villas.
        self._set_card(29)

        self.env.players[2].available_bases = 1
        self.env.players[2].available_forces[0] = 10

        self._start_event(shaded=False)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        self.env.step(self.env._target_faction_action_base + 2)  # Choose DR

        sp = self.env.board.spaces[5]  # Las Villas
        self.assertEqual(int(sp.pieces[7]), 1)  # DR Base
        self.assertEqual(int(sp.pieces[5]), 2)  # 2 DR Underground Guerrillas
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_chomon_sh_remove_or_replace_single_piece_type(self):
        # Card 29 (Fauré Chomón, Sh): Choose a DR piece type, then choose Remove vs Replace.
        self._set_card(29)

        target = 0
        sp = self.env.board.spaces[target]
        sp.pieces[5] = 1  # DR Underground
        sp.update_control()

        self.env.players[1].available_forces[0] = 5

        self._start_event(shaded=True)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + target)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        replace = self.env._event_option_action_base + 1
        self.assertEqual(int(self.env.legal_actions[replace]), 1)
        self.env.step(replace)

        self.assertEqual(int(sp.pieces[5]), 0)
        self.assertEqual(int(sp.pieces[2]), 1)  # Replaced with M26 Underground
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_chomon_sh_remove_or_replace_base_piece_type(self):
        # Card 29 (Fauré Chomón, Sh): Replace a DR Base with an M26 Base if available.
        self._set_card(29)

        target = 5  # Las Villas
        sp = self.env.board.spaces[target]
        sp.pieces[7] = 1  # DR Base
        sp.update_control()

        self.env.players[1].available_bases = 1

        self._start_event(shaded=True)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        self.env.step(self.env._target_space_action_base + target)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_EVENT_OPTION)

        replace = self.env._event_option_action_base + 1
        self.assertEqual(int(self.env.legal_actions[replace]), 1)
        self.env.step(replace)

        self.assertEqual(int(sp.pieces[7]), 0)
        self.assertEqual(int(sp.pieces[4]), 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
