import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_UNSHADED,
    PHASE_CHOOSE_TARGET_SPACE,
    PHASE_CHOOSE_TARGET_FACTION,
    PHASE_CHOOSE_MAIN,
)


class TestLlanoUnshadedTargetSelection(unittest.TestCase):
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
            sp.update_control()

        self.env.players[1].available_bases = 10
        self.env.players[1].available_forces[0] = 10
        self.env.players[2].available_forces[0] = 10
        self.env.players[3].available_forces[0] = 10

    def test_llano_unshaded_places_m26_base_and_any_guerrilla(self):
        d = EVENT_DECK_DATA[42]
        self.env.current_card = Card(42, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        target = 3  # Havana (City)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_UNSHADED)

        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_SPACE)
        pick_target = self.env._target_space_action_base + target
        self.assertEqual(int(self.env.legal_actions[pick_target]), 1)
        self.env.step(pick_target)

        # Should now ask for guerrilla faction.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_TARGET_FACTION)

        # Pick DR as the guerrilla faction.
        choose_dr = self.env._target_faction_action_base + 2
        self.assertEqual(int(self.env.legal_actions[choose_dr]), 1)

        before_m26_base = int(self.env.board.spaces[target].pieces[4])
        before_dr_u = int(self.env.board.spaces[target].pieces[5])

        self.env.step(choose_dr)

        # Base was already placed on the target-space step.
        self.assertEqual(int(self.env.board.spaces[target].pieces[4]), before_m26_base)
        self.assertEqual(int(self.env.board.spaces[target].pieces[5]), before_dr_u + 1)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
