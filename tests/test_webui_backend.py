
import sys
import os
import unittest
from fastapi.testclient import TestClient

# Add project root to path
sys.path.append(os.getcwd())

from webui.backend.app.main import app
from webui.backend.app.env_instance import env_instance
from app.environments.cubalibre.envs.env import PHASE_CHOOSE_TARGET_FACTION, PHASE_CHOOSE_TARGET_SPACE

class TestWebUIBackend(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Reset env via API
        self.client.post("/reset")
        self.env = env_instance.get()

    def test_state_structure(self):
        response = self.client.get("/state")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("pending", data)
        self.assertIn("faction", data["pending"])
        self.assertIn("option", data["pending"])
        self.assertIn("target", data["pending"])

    def test_pending_faction_exposure(self):
        """Test that PHASE_CHOOSE_TARGET_FACTION exposes allowed factions in pending state."""
        # Force env into a state with pending faction choice
        # Example: Election (Unshaded) - Card 7
        self.env.phase = PHASE_CHOOSE_TARGET_FACTION
        self.env._pending_event_faction = {
            "event": "TEST_EVENT",
            "allowed": [1, 2, 3]
        }
        
        response = self.client.get("/state")
        data = response.json()
        
        pending_faction = data["pending"]["faction"]
        self.assertIsNotNone(pending_faction)
        self.assertEqual(pending_faction["event"], "TEST_EVENT")
        self.assertEqual(pending_faction["allowed"], [1, 2, 3])

    def test_pending_target_exposure(self):
        """Test that PHASE_CHOOSE_TARGET_SPACE exposes the event/op name."""
        self.env.phase = PHASE_CHOOSE_TARGET_SPACE
        self.env._pending_event_target = {
            "event": "TEST_TARGET_EVENT",
            "count": 0
        }
        
        response = self.client.get("/state")
        data = response.json()
        
        pending_target = data["pending"]["target"]
        self.assertIsNotNone(pending_target)
        self.assertEqual(pending_target["event"], "TEST_TARGET_EVENT")

if __name__ == "__main__":
    unittest.main()
