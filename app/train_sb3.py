import os
import argparse
import time
import gymnasium as gym
import numpy as np
import torch as th

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.utils import set_random_seed

from utils.register import get_environment, get_network_arch
import config

def main(args):
    # Determine device
    device = "cuda" if th.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Directories
    model_dir = os.path.join(config.MODELDIR, args.env_name)
    os.makedirs(model_dir, exist_ok=True)
    os.makedirs(config.LOGDIR, exist_ok=True)

    # Set seed
    set_random_seed(args.seed)

    # Get Environment Class & Policy Class
    EnvClass = get_environment(args.env_name)
    env_kwargs = {}
    if args.env_name == "cubalibre":
        env_kwargs["same_player_control"] = False
    PolicyClass = get_network_arch(args.env_name)

    # Create Training Environment (Vectorized)
    # Using DummyVecEnv for simplicity/debugging, but SubprocVecEnv is better for speed
    train_env = make_vec_env(lambda: EnvClass(verbose=False, **env_kwargs), n_envs=4, seed=args.seed, vec_env_cls=DummyVecEnv)
    
    # Create Eval Environment
    eval_env = EnvClass(verbose=False, **env_kwargs)

    # CustomPolicy already defines the extractor in its __init__, 
    # so we don't need to extract it here.
    # We can pass net_arch if we want to override, or leave it to the Policy to decide.
    policy_kwargs = dict(
       net_arch=dict(pi=[256, 256], vf=[256, 256])
    )
    
    # If the CustomPolicy class is a full ActorCriticPolicy subclass (which it is), 
    # we pass it directly to PPO.
    
    print(f"Initializing PPO agent for {args.env_name}...")
    
    model = PPO(
        PolicyClass,
        train_env,
        verbose=1,
        learning_rate=args.optim_stepsize,
        n_steps=args.timesteps_per_actorbatch,
        batch_size=args.optim_batchsize,
        n_epochs=args.optim_epochs,
        gamma=args.gamma,
        gae_lambda=args.lam,
        clip_range=args.clip_param,
        ent_coef=args.entcoeff,
        tensorboard_log=config.LOGDIR,
        device=device
    )

    # Callbacks
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=model_dir,
        log_path=config.LOGDIR,
        eval_freq=args.eval_freq,
        n_eval_episodes=args.n_eval_episodes,
        deterministic=True,
        render=False
    )

    print("Starting training...")
    try:
        model.learn(total_timesteps=args.total_timesteps, callback=eval_callback, tb_log_name=f"{args.env_name}_ppo")
    except KeyboardInterrupt:
        print("Training interrupted. Saving current model...")
    
    model.save(os.path.join(model_dir, "final_model"))
    print("Training complete.")
    train_env.close()

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env_name", "-e", type=str, required=True, help="Environment name")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed")
    parser.add_argument("--total_timesteps", type=int, default=1000000, help="Total training timesteps")
    
    # PPO Hyperparams (defaults from original script where possible)
    parser.add_argument("--timesteps_per_actorbatch", "-tpa", type=int, default=2048, help="n_steps")
    parser.add_argument("--optim_batchsize", "-ob", type=int, default=64, help="batch_size")
    parser.add_argument("--optim_epochs", "-oe", type=int, default=10, help="n_epochs")
    parser.add_argument("--optim_stepsize", "-os", type=float, default=3e-4, help="learning_rate")
    parser.add_argument("--gamma", "-g", type=float, default=0.99, help="gamma")
    parser.add_argument("--lam", "-l", type=float, default=0.95, help="gae_lambda")
    parser.add_argument("--clip_param", "-c", type=float, default=0.2, help="clip_range")
    parser.add_argument("--entcoeff", "-ent", type=float, default=0.0, help="ent_coef")
    
    parser.add_argument("--eval_freq", "-ef", type=int, default=10000, help="Evaluation frequency")
    parser.add_argument("--n_eval_episodes", "-ne", type=int, default=10, help="Eval episodes")

    args = parser.parse_args()
    main(args)

if __name__ == "__main__":
    cli()
