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


class TestCard44RebelAirForce(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

        for p in self.env.players:
            p.eligible = True
            p.resources = 0

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

    def test_unshaded_requires_rebel_faction_choice_then_free_ambush_bases_first(self):
        # Unshaded: Select M26 or DR; a guerrilla (active or underground) free Ambushes Govt forces; remove Bases first.
        self._set_card(44)

        target = 11  # Sierra Maestra
        self.env.board.spaces[target].pieces[3] = 1  # M26 active guerrilla qualifies
        self.env.board.spaces[target].govt_bases = 1
        self.env.board.spaces[target].pieces[0] = 2

        before_bases = int(self.env.board.spaces[target].govt_bases)
        before_cubes = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self._start_event(shaded=False, acting_player=0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        choose_m26 = self.env._target_faction_action_base + 1
        self.assertEqual(int(self.env.legal_actions[choose_m26]), 1)
        self.env.step(choose_m26)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_target = self.env._target_space_action_base + target
        self.assertEqual(int(self.env.legal_actions[pick_target]), 1)
        self.env.step(pick_target)

        after_bases = int(self.env.board.spaces[target].govt_bases)
        after_cubes = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self.assertEqual(after_bases, max(0, before_bases - 1))
        self.assertLessEqual(after_cubes, before_cubes)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_shaded_choose_faction_and_transfer_die_roll_resources_to_syndicate(self):
        self._set_card(44)

        self.env.players[0].resources = 10
        self.env.players[1].resources = 6
        self.env.players[2].resources = 0
        self.env.players[3].resources = 0

        self.env._roll_die = lambda: 4

        self._start_event(shaded=True, acting_player=0)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        choose_m26 = self.env._target_faction_action_base + 1
        self.assertEqual(int(self.env.legal_actions[choose_m26]), 1)

        self.env.step(choose_m26)

        self.assertEqual(self.env.players[0].resources, 10)
        self.assertEqual(self.env.players[1].resources, 2)
        self.assertEqual(self.env.players[3].resources, 4)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
