import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    PHASE_CHOOSE_MAIN,
    PHASE_CHOOSE_LIMITED_OP_ACTION,
    PHASE_CHOOSE_SPECIAL_ACTIVITY,
    MAIN_PASS,
    OP_TRAIN_FORCE,
    OP_AIR_STRIKE,
)


@unittest.skip("Covered by tests/cubalibre/test_card_10_map.py")
class TestMapShadedFreeSaWithLimitedOps(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)
        self.env.reset(seed=123)

    def test_govt_limited_ops_allows_free_sa_when_map_shaded(self):
        # Ensure MAP_Shaded is active.
        self.env.capabilities.add("MAP_Shaded")

        # Use any non-propaganda card; we only need Limited Ops context.
        d = EVENT_DECK_DATA[8]
        self.env.current_card = Card(8, d["name"], d["order"], d["unshaded"], d["shaded"])

        # Force Govt as second actor (Limited Ops).
        self.env.card_action_slot = 1
        self.env.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.players[0].resources = 10
        self.env.players[0].available_forces[0] = 10

        # Make Air Strike legal in SA phase: need active guerrilla in a Province/Mountain.
        sierra = 11  # Sierra Maestra (mountain)
        self.env.board.spaces[sierra].pieces[3] = 1  # active M26 guerrilla

        # Choose a Limited Op that should be legal: Train Force in Havana (city).
        havana = 3
        train = self.env._limited_ops_action_base + OP_TRAIN_FORCE * self.env.num_spaces + havana
        self.assertEqual(self.env.legal_actions[train], 1)

        # Make the next card deterministic so we can assert advancement after slot 2.
        next_d = EVENT_DECK_DATA[7]
        self.env.deck.cards = [Card(7, next_d["name"], next_d["order"], next_d["unshaded"], next_d["shaded"])]

        self.env.step(train)

        # Should transition to SA phase without consuming the slot yet.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_SPECIAL_ACTIVITY)
        self.assertEqual(self.env.card_action_slot, 1)

        # Air Strike should now be legal as the free SA.
        airstrike = self.env._ops_action_base + OP_AIR_STRIKE * self.env.num_spaces + sierra
        self.assertEqual(self.env.legal_actions[airstrike], 1)

        self.env.step(airstrike)

        # Completing SA consumes the slot, which advances to the next card and resets slot to 0.
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)
        self.assertEqual(self.env.card_action_slot, 0)
        self.assertEqual(self.env.current_card.id, 7)


if __name__ == "__main__":
    unittest.main()
