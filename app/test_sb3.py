import argparse
import os
import gymnasium as gym
import numpy as np
import torch as th
from stable_baselines3 import PPO

from utils.register import get_environment
import config

def main(args):
    print(f"Loading environment: {args.env_name}")
    EnvClass = get_environment(args.env_name)
    env_kwargs = {}
    if args.env_name == "cubalibre":
        env_kwargs["same_player_control"] = False
    env = EnvClass(verbose=True, manual=False, **env_kwargs)
    
    # Load Model
    model_path = os.path.join(config.MODELDIR, args.env_name, "final_model.zip")
    if args.model_path:
        model_path = args.model_path
        
    print(f"Loading model from: {model_path}")
    if os.path.exists(model_path):
        model = PPO.load(model_path)
    else:
        print("⚠ Model not found! Playing with Random Agent for non-human players.")
        model = None

    obs, _ = env.reset(seed=args.seed)
    done = False
    
    human_player_idx = args.human_player
    print(f"You are playing as Player {human_player_idx} ({env.factions_list[human_player_idx]})")
    
    while not done:
        current_player = env.current_player_num
        env.render()
        
        mask = env.legal_actions
        legal_indices = [i for i, x in enumerate(mask) if x == 1]
        
        action = None
        
        if current_player == human_player_idx:
            print(f"\nYour Turn ({env.factions_list[current_player]})!")
            print(f"Legal Actions: {legal_indices}")
            while True:
                try:
                    inp = input("Enter Action ID: ")
                    if inp.lower() == 'q': return
                    act = int(inp)
                    if act in legal_indices:
                        action = act
                        break
                    else:
                        print("Invalid/Illegal Action. Try again.")
                except ValueError:
                    print("Please enter a number.")
        else:
            # AI Turn
            if model:
                # SB3 predict returns (action, state)
                # We need to handle action masking if possible, but standard PPO predict doesn't take mask easily unless wrapped.
                # For now, we trust the model or fallback to random if invalid.
                # Ideally config `action_masks` in env if using MaskablePPO, but here we are using standard PPO.
                # We can simple sample loop or just take best.
                action, _ = model.predict(obs, deterministic=False) # deterministic=False to see variety
                if mask[action] == 0:
                   # Fallback if model picks illegal move (since we aren't using MaskablePPO yet)
                   # For a complex game like this, Action Masking is critical. 
                   # Standard PPO might struggle without it.
                   # For this test script, we filter.
                   # Force valid random if invalid
                   # A better approach is "predict_proba" and mask, but SB3 standard PPO predict doesn't expose probas easily.
                   action = np.random.choice(legal_indices)
            else:
                action = np.random.choice(legal_indices)
                
            print(f"\nAI ({env.factions_list[current_player]}) playing Action {action}")
            
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        
        if done:
            print("\nGAME OVER")
            env.resolve_propaganda()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--env_name", "-e", type=str, default="cubalibre")
    parser.add_argument("--human_player", "-p", type=int, default=0, help="Index of human player (0=Govt)")
    parser.add_argument("--seed", "-s", type=int, default=42)
    parser.add_argument("--model_path", "-m", type=str, default=None)
    args = parser.parse_args()
    main(args)
