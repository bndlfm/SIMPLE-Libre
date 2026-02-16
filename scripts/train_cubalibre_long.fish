#!/usr/bin/env nix
#! nix develop --command fish
# Long-run training for Cuba Libre (sb3-contrib MaskablePPO).
# Usage:
#   ./scripts/train_cubalibre_long.fish [options]
#
# Options:
#   reset              Start training from scratch (delete existing models)
#   --load PATH        Resume training from a specific model .zip file

set args_list
set i 1
while test $i -le (count $argv)
    switch $argv[$i]
        case reset
            set args_list $args_list --reset
        case --load
            set i (math $i + 1)
            if test $i -le (count $argv)
                set args_list $args_list --load $argv[$i]
            else
                echo "Error: --load requires a path argument"
                exit 1
            end
        case '*'
            echo "Unknown option: $argv[$i]"
            exit 1
    end
    set i (math $i + 1)
end

set repo_root (pwd)
set -gx PYTHONPATH "$repo_root/app:$repo_root/app/environments"

# Use the local venv if present.
if test -f "$repo_root/.venv/bin/activate.fish"
    source "$repo_root/.venv/bin/activate.fish"
end

python app/train.py \
    --env_name cubalibre \
    --eval_freq 20000 \
    --n_eval_episodes 5 \
    --timesteps_per_actorbatch 256 \
    --optim_batchsize 64 \
    --optim_epochs 10 \
    $args_list
