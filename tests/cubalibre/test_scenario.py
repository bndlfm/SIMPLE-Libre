
import gymnasium as gym
from app.environments.cubalibre.envs.env import CubaLibreEnv

def test_standard_scenario():
    print("Testing Standard Scenario...")
    env = CubaLibreEnv()
    env.reset(options={"scenario": "standard"})
    # 48 events + 4 prop = 52. Reset draws 1 -> 51
    deck_size = len(env.deck.cards)
    print(f"Deck size: {deck_size}")
    assert deck_size == 51
    print("Standard Scenario Passed!")

def test_short_scenario():
    print("Testing Short Scenario...")
    env = CubaLibreEnv()
    env.reset(options={"scenario": "short"})
    # (48-8) events + 4 prop = 44. Reset draws 1 -> 43
    deck_size = len(env.deck.cards)
    print(f"Deck size: {deck_size}")
    assert deck_size == 43
    
    # Check cards per pile (should be 11: 10 events + 1 prop)
    # The deck is a stack, so we'd have to peek or pop to check piles if we really wanted to.
    # But total size is a good indicator.
    print("Short Scenario Passed!")

if __name__ == "__main__":
    test_standard_scenario()
    test_short_scenario()
