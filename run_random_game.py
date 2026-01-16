import gymnasium as gym
import sys
import os

# Add app to path
sys.path.append(os.path.join(os.getcwd(), 'app'))
sys.path.append(os.path.join(os.getcwd(), 'app/environments'))

from cubalibre.envs.env import CubaLibreEnv

def run_simulation(steps=500):
    env = CubaLibreEnv(verbose=True, same_player_control=False)
    env.reset()
    
    for i in range(steps):
        # Pick a random legal action
        mask = env.legal_actions
        legal_indices = [idx for idx, val in enumerate(mask) if val == 1]
        
        if not legal_indices:
            print("No legal actions! Game over / Stuck?")
            break
            
        import random
        action = random.choice(legal_indices)
        
        obs, reward, terminated, truncated, info = env.step(action)
        
        if terminated or truncated:
            print(f"Game finished at step {i}")
            break
            
    print("Simulation finished.")

if __name__ == "__main__":
    run_simulation()
