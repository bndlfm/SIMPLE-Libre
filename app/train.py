# docker-compose exec app python3 train.py -r -e cubalibre

import os
import logging
import argparse
import time
from shutil import copyfile

import torch as th
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import EvalCallback
from stable_baselines3.common.utils import set_random_seed

from utils.callbacks import SelfPlayCallback
from utils.files import reset_logs, reset_models
from utils.register import get_network_arch, get_environment
from utils.selfplay import selfplay_wrapper

import config

logger = logging.getLogger(__name__)

def main(args):

  logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

  device = "cuda" if th.cuda.is_available() else "cpu"
  logger.info(f"Using device: {device}")

  model_dir = os.path.join(config.MODELDIR, args.env_name)
  os.makedirs(model_dir, exist_ok=True)
  os.makedirs(config.TMPMODELDIR, exist_ok=True)
  os.makedirs(config.LOGDIR, exist_ok=True)

  reset_logs(model_dir)
  if args.reset:
    reset_models(model_dir)

  set_random_seed(args.seed)

  logger.info('\nSetting up the selfplay training environment opponents...')
  base_env = get_environment(args.env_name)
  env_kwargs = {}
  if args.env_name == "cubalibre":
    env_kwargs["same_player_control"] = False
  env = selfplay_wrapper(base_env, env_kwargs=env_kwargs)(opponent_type = args.opponent_type, verbose = args.verbose)

  CustomPolicy = get_network_arch(args.env_name)

  if args.reset or not os.path.exists(os.path.join(model_dir, 'best_model.zip')):
    logger.info('\nCreating new PPO agent to train...')
    model = PPO(
      CustomPolicy,
      env,
      learning_rate=args.optim_stepsize,
      n_steps=args.timesteps_per_actorbatch,
      batch_size=args.optim_batchsize,
      n_epochs=args.optim_epochs,
      gamma=args.gamma,
      gae_lambda=args.lam,
      clip_range=args.clip_param,
      ent_coef=args.entcoeff,
      verbose=1,
      tensorboard_log=config.LOGDIR,
      device=device,
    )
  else:
    logger.info('\nLoading the best_model.zip PPO agent to continue training...')
    model = PPO.load(os.path.join(model_dir, 'best_model.zip'), env=env, device=device)
    model.learning_rate = args.optim_stepsize
    model.n_steps = args.timesteps_per_actorbatch
    model.batch_size = args.optim_batchsize
    model.n_epochs = args.optim_epochs
    model.gamma = args.gamma
    model.gae_lambda = args.lam
    model.clip_range = lambda _: args.clip_param
    model.ent_coef = args.entcoeff
    model.tensorboard_log = config.LOGDIR

  #Callbacks
  logger.info('\nSetting up the selfplay evaluation environment opponents...')
  callback_args = {
    'eval_env': selfplay_wrapper(base_env, env_kwargs=env_kwargs)(opponent_type = args.opponent_type, verbose = args.verbose),
    'best_model_save_path' : config.TMPMODELDIR,
    'log_path' : config.LOGDIR,
    'eval_freq' : args.eval_freq,
    'n_eval_episodes' : args.n_eval_episodes,
    'deterministic' : False,
    'render' : True,
    'verbose' : 0
  }

  if args.rules:  
    logger.info('\nSetting up the evaluation environment against the rules-based agent...')
    eval_actual_callback = EvalCallback(
      eval_env = selfplay_wrapper(base_env, env_kwargs=env_kwargs)(opponent_type = 'rules', verbose = args.verbose),
      eval_freq=1,
      n_eval_episodes=args.n_eval_episodes,
      deterministic = args.best,
      render = True,
      verbose = 0
    )
    callback_args['callback_on_new_best'] = eval_actual_callback
    
  # Evaluate the agent against previous versions
  eval_callback = SelfPlayCallback(args.opponent_type, args.threshold, args.env_name, **callback_args)

  logger.info('\nSetup complete - commencing learning...\n')

  model.learn(total_timesteps=int(1e9), callback=[eval_callback], reset_num_timesteps = False, tb_log_name="tb")

  env.close()
  del env


def cli() -> None:
  """Handles argument extraction from CLI and passing to main().
  Note that a separate function is used rather than in __name__ == '__main__'
  to allow unit testing of cli().
  """
  # Setup argparse to show defaults on help
  formatter_class = argparse.ArgumentDefaultsHelpFormatter
  parser = argparse.ArgumentParser(formatter_class=formatter_class)


  parser.add_argument("--reset", "-r", action = 'store_true', default = False
                , help="Start retraining the model from scratch")
  parser.add_argument("--opponent_type", "-o", type = str, default = 'mostly_best'
              , help="best / mostly_best / random / base / rules - the type of opponent to train against")
  parser.add_argument("--debug", "-d", action = 'store_true', default = False
              , help="Debug logging")
  parser.add_argument("--verbose", "-v", action = 'store_true', default = False
              , help="Show observation in debug output")
  parser.add_argument("--rules", "-ru", action = 'store_true', default = False
              , help="Evaluate on a ruled-based agent")
  parser.add_argument("--best", "-b", action = 'store_true', default = False
              , help="Uses best moves when evaluating agent against rules-based agent")
  parser.add_argument("--env_name", "-e", type = str, default = 'tictactoe'
              , help="Which gym environment to train in: tictactoe, connect4, sushigo, butterfly, geschenkt, frouge")
  parser.add_argument("--seed", "-s",  type = int, default = 17
            , help="Random seed")

  parser.add_argument("--eval_freq", "-ef",  type = int, default = 10240
            , help="How many timesteps should each actor contribute before the agent is evaluated?")
  parser.add_argument("--n_eval_episodes", "-ne",  type = int, default = 100
            , help="How many episodes should each actor contirbute to the evaluation of the agent")
  parser.add_argument("--threshold", "-t",  type = float, default = 0.2
            , help="What score must the agent achieve during evaluation to 'beat' the previous version?")
  parser.add_argument("--gamma", "-g",  type = float, default = 0.99
            , help="The value of gamma in PPO")
  parser.add_argument("--timesteps_per_actorbatch", "-tpa",  type = int, default = 1024
            , help="How many timesteps should each actor contribute to the batch?")
  parser.add_argument("--clip_param", "-c",  type = float, default = 0.2
            , help="The clip paramater in PPO")
  parser.add_argument("--entcoeff", "-ent",  type = float, default = 0.1
            , help="The entropy coefficient in PPO")

  parser.add_argument("--optim_epochs", "-oe",  type = int, default = 4
            , help="The number of epoch to train the PPO agent per batch")
  parser.add_argument("--optim_stepsize", "-os",  type = float, default = 0.0003
            , help="The step size for the PPO optimiser")
  parser.add_argument("--optim_batchsize", "-ob",  type = int, default = 1024
            , help="The minibatch size in the PPO optimiser")
            
  parser.add_argument("--lam", "-l",  type = float, default = 0.95
            , help="The value of lambda in PPO")

  # Extract args
  args = parser.parse_args()

  # Enter main
  main(args)
  return


if __name__ == '__main__':
  cli()
