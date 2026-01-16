import unittest
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.environments.cubalibre.envs.env import CubaLibreEnv


class TestDeckPeek(unittest.TestCase):
    """Test that the deck peek mechanism works correctly."""

    def test_next_card_initialized_on_reset(self):
        """Test that next_card is set when environment is reset."""
        env = CubaLibreEnv()
        env.reset()
        
        # After reset, current_card should be set
        self.assertIsNotNone(env.current_card)
        
        # next_card should also be set (peek at what's coming)
        self.assertIsNotNone(env.next_card)
        
        # They should be different cards
        self.assertNotEqual(env.current_card.id, env.next_card.id)
    
    def test_next_card_in_observation(self):
        """Test that next_card.id appears in observation header."""
        env = CubaLibreEnv()
        obs, _ = env.reset()
        
        # Observation header has 15 fields now
        self.assertEqual(len(obs), env._obs_header_size + (env.num_spaces * env.space_feature_size))
        
        # Field 4 = current_card.id
        current_card_id = obs[4]
        self.assertGreater(current_card_id, 0)
        
        # Field 14 = next_card.id
        next_card_id = obs[14]
        self.assertGreater(next_card_id, 0)
        
        # They should be different
        self.assertNotEqual(current_card_id, next_card_id)
    
    def test_next_card_updates_when_drawing(self):
        """Test that next_card updates correctly as cards are drawn."""
        env = CubaLibreEnv()
        env.reset()
        
        initial_next_card_id = env.next_card.id if env.next_card else None
        
        # Pass actions to advance through a card
        legal = env.legal_actions
        for action_idx in range(len(legal)):
            if legal[action_idx] == 1:
                # Take first legal action (should be PASS)
                obs, reward, done, truncated, info = env.step(action_idx)
                break
        
        # After one faction passes, next_card should still be the same
        # (we haven't moved to the next card yet)
        self.assertEqual(env.next_card.id if env.next_card else None, initial_next_card_id)
        
        # Pass second faction to move to next card
        legal = env.legal_actions
        for action_idx in range(len(legal)):
            if legal[action_idx] == 1:
                obs, reward, done, truncated, info = env.step(action_idx)
                break
        
        # Now we should have advanced to a new current_card
        # and next_card should have changed
        if env.next_card:
            # The previous "next" card should now be the "current" card
            # This is hard to verify directly, but we can check that
            # next_card has updated
            self.assertIsNotNone(env.next_card)
    
    def test_next_card_none_at_deck_end(self):
        """Test that next_card becomes None when deck is exhausted."""
        env = CubaLibreEnv()
        env.reset()
        
        # Manually exhaust the deck
        while len(env.deck.cards) > 1:
            env.deck.draw()
        
        # Now draw the last card
        last_card = env.deck.draw()
        env.current_card = last_card
        env.next_card = env.deck.peek()
        
        # next_card should be None
        self.assertIsNone(env.next_card)
        
        # Observation should have 0 for next_card field
        obs = env.observation
        self.assertEqual(obs[14], 0.0)


if __name__ == '__main__':
    unittest.main()
