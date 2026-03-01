import os
import logging
import json
import time
import numpy as np
from shutil import copyfile

from sb3_contrib.common.maskable.callbacks import MaskableEvalCallback

from utils.files import get_best_model_name, get_model_stats

import config

logger = logging.getLogger(__name__)

class SelfPlayCallback(MaskableEvalCallback):
  def __init__(self, opponent_type, threshold, env_name, *args, **kwargs):
    super(SelfPlayCallback, self).__init__(*args, **kwargs)
    self.opponent_type = opponent_type
    self.model_dir = os.path.join(config.MODELDIR, env_name)
    self.generation, self.base_timesteps, pbmr, bmr = get_model_stats(get_best_model_name(env_name))

    #reset best_mean_reward because this is what we use to extract the rewards from the latest evaluation by each agent
    self.best_mean_reward = -np.inf
    if self.callback is not None: #if evaling against rules-based agent as well, reset this too
      self.callback.best_mean_reward = -np.inf

    if self.opponent_type == 'rules':
      self.threshold = bmr # the threshold is the overall best evaluation by the agent against a rules-based agent
    else:
      self.threshold = threshold # the threshold is a constant




  def _log_to_jsonl(self, metrics: dict):
    try:
      log_path = os.path.join(config.LOGDIR, "training.jsonl")
      with open(log_path, "a") as f:
        f.write(json.dumps(metrics) + "\n")
    except Exception as e:
      logger.error(f"Failed to log to JSONL: {e}")

  def _on_step(self) -> bool:
    
    # Log intermediate training progress every 1000 steps
    if self.n_calls % 1000 == 0:
      metrics = {
        "timestamp": time.time(),
        "timesteps": self.num_timesteps,
        "generation": self.generation,
        "best_mean_reward": float(self.threshold),
        "status": "training" 
      }
      self._log_to_jsonl(metrics)

    if self.eval_freq > 0 and self.n_calls % self.eval_freq == 0:

      result = super(SelfPlayCallback, self)._on_step() #this will set self.best_mean_reward to the reward from the evaluation as it's previously -np.inf

      av_reward = self.best_mean_reward
      std_reward = 0.0
      total_episodes = self.n_eval_episodes

      if self.callback is not None:
        av_rules_based_reward = self.callback.best_mean_reward
      else:
        av_rules_based_reward = 0.0

      logger.info("Eval num_timesteps={}, episode_reward={:.2f} +/- {:.2f}".format(self.num_timesteps, av_reward, std_reward))
      logger.info("Total episodes ran={}".format(total_episodes))

      # Log to JSONL for WebUI
      metrics = {
        "timestamp": time.time(),
        "timesteps": self.num_timesteps,
        "generation": self.generation,
        "best_mean_reward": float(self.threshold),
        "eval_mean_reward": float(av_reward),
        "eval_std_reward": float(std_reward),
        "rules_based_reward": float(av_rules_based_reward),
        "status": "eval"
      }
      self._log_to_jsonl(metrics)

      #compare the latest reward against the threshold
      if result and av_reward > self.threshold:
        self.generation += 1
        logger.info(f"New best model: {self.generation}\n")

        generation_str = str(self.generation).zfill(5)
        av_rewards_str = str(round(av_reward,3))

        if self.callback is not None:
          av_rules_based_reward_str = str(round(av_rules_based_reward,3))
        else:
          av_rules_based_reward_str = str(0)
        
        source_file = os.path.join(config.TMPMODELDIR, f"best_model.zip") # this is constantly being written to - not actually the best model
        target_file = os.path.join(self.model_dir,  f"_model_{generation_str}_{av_rules_based_reward_str}_{av_rewards_str}_{str(self.base_timesteps + self.num_timesteps)}_.zip")
        copyfile(source_file, target_file)
        target_file = os.path.join(self.model_dir,  f"best_model.zip")
        copyfile(source_file, target_file)

        # if playing against a rules based agent, update the global best reward to the improved metric
        if self.opponent_type == 'rules':
          self.threshold  = av_reward
        
      #reset best_mean_reward because this is what we use to extract the rewards from the latest evaluation by each agent
      self.best_mean_reward = -np.inf

      if self.callback is not None: #if evaling against rules-based agent as well, reset this too
        self.callback.best_mean_reward = -np.inf

    return True