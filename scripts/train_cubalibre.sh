#!/bin/bash
# Script to train CubaLibre agent using PPO
# Usage: ./scripts/train_cubalibre.sh [reset]

RESET=""
if [ "$1" == "reset" ]; then
    RESET="-r"
fi

# Run training
# -e cubalibre: Environment name
# -tpa 128: Timesteps per actor batch (lower for faster updates during testing)
# -n_eval_episodes 10: Fewer eval episodes for faster feedback loop
export PYTHONPATH=$PYTHONPATH:$(pwd)/app:$(pwd)/app/environments
.venv/bin/python3 app/train_sb3.py --env_name cubalibre --timesteps_per_actorbatch 128 --n_eval_episodes 10
