import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    EVENT_UNSHADED,
    MAIN_EVENT,
    OP_AIR_STRIKE,
    OP_TRAIN_FORCE,
    OP_TRANSPORT,
    PHASE_CHOOSE_EVENT_SIDE,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_TARGET_SPACE,
)


class TestCard10Map(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def _set_current_card(self, card_id: int):
        d = EVENT_DECK_DATA[card_id]
        self.env.current_card = Card(card_id, d["name"], d["order"], d["unshaded"], d["shaded"])

    def test_map_unshaded_replace_cube_with_two_guerrillas(self):
        for sp in self.env.board.spaces:
            sp.pieces[:] = 0
            sp.govt_bases = 0
            sp.terror = 0
            sp.alignment = 0
            sp.support_active = False
            sp.update_control()

        self._set_current_card(10)

        self.env.current_player_num = 0
        for p in self.env.players:
            p.eligible = True

        self.env.phase = PHASE_CHOOSE_MAIN
        self.env.card_action_slot = 0

        target = 3  # Havana
        self.env.board.spaces[target].pieces[1] = 1  # Police cube

        self.env.players[0].available_forces[1] = 0
        self.env.players[1].available_forces[0] = 10

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_target = self.env._target_space_action_base + target
        self.assertEqual(self.env.legal_actions[pick_target], 1)

        before_m26 = int(self.env.board.spaces[target].pieces[2] + self.env.board.spaces[target].pieces[3])
        before_cubes = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self.env.step(pick_target)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        choose_m26 = self.env._target_faction_action_base + 1
        self.assertEqual(self.env.legal_actions[choose_m26], 1)
        self.env.step(choose_m26)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)
        self.assertEqual(self.env.legal_actions[choose_m26], 1)
        self.env.step(choose_m26)

        after_m26 = int(self.env.board.spaces[target].pieces[2] + self.env.board.spaces[target].pieces[3])
        after_cubes = int(self.env.board.spaces[target].pieces[0] + self.env.board.spaces[target].pieces[1])

        self.assertEqual(after_cubes, max(0, before_cubes - 1))
        self.assertEqual(after_m26, before_m26 + 2)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)

    def test_map_shaded_allows_free_sa_after_govt_limited_ops(self):
        self.env.capabilities.add("MAP_Shaded")

        self._set_current_card(8)

        self.env.card_action_slot = 1
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10
        self.env.players[0].available_forces[0] = 10

        sierra = 11
        self.env.board.spaces[sierra].pieces[3] = 1

        havana = 3
        train = self.env._limited_ops_action_base + OP_TRAIN_FORCE * self.env.num_spaces + havana
        self.assertEqual(self.env.legal_actions[train], 1)

        next_d = EVENT_DECK_DATA[7]
        self.env.deck.cards = [Card(7, next_d["name"], next_d["order"], next_d["unshaded"], next_d["shaded"])]

        self.env.step(train)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        self.assertEqual(self.env.card_action_slot, 1)

        airstrike = self.env._ops_action_base + OP_AIR_STRIKE * self.env.num_spaces + sierra
        self.assertEqual(self.env.legal_actions[airstrike], 1)

        self.env.step(airstrike)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertEqual(self.env.card_action_slot, 0)
        self.assertEqual(self.env.current_card.id, 7)

    def test_map_shaded_allows_free_sa_after_govt_limited_transport(self):
        self.env.capabilities.add("MAP_Shaded")

        self._set_current_card(8)

        self.env.card_action_slot = 1
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10

        dest = 3  # Havana
        src = 2  # La Habana
        self.env.board.spaces[src].pieces[0] = 2

        sierra = 11
        self.env.board.spaces[sierra].pieces[3] = 1

        transport = self.env._limited_ops_action_base + OP_TRANSPORT * self.env.num_spaces + dest
        self.assertEqual(self.env.legal_actions[transport], 1)

        self.env.step(transport)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)

        pick_src = self.env._target_space_action_base + src
        self.assertEqual(self.env.legal_actions[pick_src], 1)

        self.env.step(pick_src)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        self.assertEqual(self.env.card_action_slot, 1)

        airstrike = self.env._ops_action_base + OP_AIR_STRIKE * self.env.num_spaces + sierra
        self.assertEqual(self.env.legal_actions[airstrike], 1)


if __name__ == "__main__":
    unittest.main()
