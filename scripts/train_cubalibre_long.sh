#!/usr/bin/env bash
# Long-run training for Cuba Libre (sb3-contrib MaskablePPO).
# Usage:
#   ./scripts/train_cubalibre_long.sh [options]
#
# Options:
#   reset              Start training from scratch (delete existing models)
#   --load PATH        Resume training from a specific model .zip file

args_list=""

while [ $# -gt 0 ]; do
    case "$1" in
        reset)
            args_list="$args_list --reset"
            shift
            ;;
        --load)
            if [ -n "$2" ]; then
                args_list="$args_list --load $2"
                shift 2
            else
                echo "Error: --load requires a path argument"
                exit 1
            fi
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

repo_root="$(pwd)"
export PYTHONPATH="$repo_root/app:$repo_root/app/environments"

# Use the local venv if present.
if [ -f "$repo_root/.venv/bin/activate" ]; then
    source "$repo_root/.venv/bin/activate"
fi

python app/train.py \
    --env_name cubalibre \
    --eval_freq 20000 \
    --n_eval_episodes 5 \
    --timesteps_per_actorbatch 256 \
    --optim_batchsize 64 \
    --optim_epochs 10 \
    $args_list
