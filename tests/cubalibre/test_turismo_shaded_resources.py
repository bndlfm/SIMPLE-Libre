import unittest

from app.environments.cubalibre.envs.classes import Card
from app.environments.cubalibre.envs.data import EVENT_DECK_DATA
from app.environments.cubalibre.envs.env import (
    CubaLibreEnv,
    MAIN_EVENT,
    EVENT_SHADED,
    PHASE_CHOOSE_MAIN,
)


class TestTurismoShadedResources(unittest.TestCase):
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

    def test_turismo_shaded_govt_and_syn_gain_per_open_casino_with_police(self):
        d = EVENT_DECK_DATA[39]
        self.env.current_card = Card(39, d["name"], d["order"], d["unshaded"], d["shaded"])

        self.env.current_player_num = 0
        self.env.players[0].eligible = True
        self.env.phase = 0
        self.env.card_action_slot = 0

        # Two qualifying spaces: open casino + police.
        s1 = 3
        s2 = 5
        self.env.board.spaces[s1].pieces[10] = 1
        self.env.board.spaces[s1].pieces[1] = 1
        self.env.board.spaces[s2].pieces[10] = 2
        self.env.board.spaces[s2].pieces[1] = 3

        # Non-qualifying space: casino but no police.
        s3 = 0
        self.env.board.spaces[s3].pieces[10] = 1
        self.env.board.spaces[s3].pieces[1] = 0

        govt_before = int(self.env.players[0].resources)
        syn_before = int(self.env.players[3].resources)

        self.env.step(self.env._main_action_base + MAIN_EVENT)
        self.env.step(self.env._event_side_base + EVENT_SHADED)

        # 2 qualifying spaces => +6 each.
        self.assertEqual(int(self.env.players[0].resources), govt_before + 6)
        self.assertEqual(int(self.env.players[3].resources), syn_before + 6)
        self.assertEqual(self.env.phase, PHASE_CHOOSE_MAIN)


if __name__ == "__main__":
    unittest.main()
