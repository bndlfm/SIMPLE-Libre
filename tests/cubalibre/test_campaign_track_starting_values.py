import unittest

from app.environments.cubalibre.envs.constants import US_ALLIANCE_FIRM
from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestCampaignTrackStartingValues(unittest.TestCase):
    def setUp(self):
        self.env = CubaLibreEnv(verbose=False, manual=False)

    def test_reset_sets_aid_and_us_alliance(self):
        self.env.reset(seed=123)
        self.assertEqual(self.env.aid, 15)
        self.assertEqual(self.env.us_alliance, US_ALLIANCE_FIRM)


if __name__ == "__main__":
    unittest.main()
