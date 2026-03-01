import sys
import logging
import numpy as np
np.set_printoptions(threshold=sys.maxsize)
import random
import string

import torch as th

logger = logging.getLogger(__name__)

def sample_action(action_probs):
    # np.random.choice is extremely strict: probabilities must sum to exactly 1.0
    p = np.asarray(action_probs, dtype=np.float64)
    p = np.maximum(p, 0.0)  # clip any negative noise
    total = p.sum()
    if total > 0:
        p = p / total
    else:
        p = np.ones_like(p) / len(p)
    # Compensate for IEEE 754 rounding error by adjusting the largest element
    remainder = 1.0 - p.sum()
    if remainder != 0.0:
        p[np.argmax(p)] += remainder
    action = np.random.choice(len(p), p=p)
    return action


def mask_actions(legal_actions, action_probs):
    masked_action_probs = np.multiply(legal_actions, action_probs)
    total = np.sum(masked_action_probs)
    if total > 0:
        masked_action_probs = masked_action_probs / total
    else:
        # All legal actions have zero probability — fall back to uniform over legal actions
        n_legal = np.sum(legal_actions)
        if n_legal > 0:
            masked_action_probs = legal_actions / n_legal
    # Ensure probabilities sum to exactly 1.0 for np.random.choice
    masked_action_probs = masked_action_probs / masked_action_probs.sum() if masked_action_probs.sum() > 0 else masked_action_probs
    return masked_action_probs


def get_action_probs_sb3(model, observation):
    """Extract action probabilities from an SB3 PPO model."""
    obs = np.asarray(observation, dtype=np.float32)
    obs_tensor = th.as_tensor(obs, dtype=th.float32, device=model.device)
    if obs_tensor.ndim == 1:
        obs_tensor = obs_tensor.unsqueeze(0)
    dist = model.policy.get_distribution(obs_tensor)
    probs = dist.distribution.probs.detach().cpu().numpy()
    if probs.ndim > 1:
        probs = probs[0]
    return probs


def get_value_sb3(model, observation):
    """Extract value estimate from an SB3 PPO model."""
    obs = np.asarray(observation, dtype=np.float32)
    obs_tensor = th.as_tensor(obs, dtype=th.float32, device=model.device)
    if obs_tensor.ndim == 1:
        obs_tensor = obs_tensor.unsqueeze(0)
    value = model.policy.predict_values(obs_tensor)
    return value.item()


class Agent():
  def __init__(self, name, model = None):
      self.name = name
      self.id = self.name + '_' + ''.join(random.choice(string.ascii_lowercase) for x in range(5))
      self.model = model
      self.points = 0

  def print_top_actions(self, action_probs):
    top5_action_idx = np.argsort(-action_probs)[:5]
    top5_actions = action_probs[top5_action_idx]
    logger.debug(f"Top 5 actions: {[str(i) + ': ' + str(round(a,2))[:5] for i,a in zip(top5_action_idx, top5_actions)]}")

  def choose_action(self, env, choose_best_action, mask_invalid_actions):
      if self.name == 'rules':
        action_probs = np.array(env.rules_move())
        action = np.argmax(action_probs) # Rules agent returns a one-hot or prob distribution? Usually one-hot.
        # Actually rules_move returns 0s and 1s? Let's assume it returns a distribution or valid move.
        # Original code: action_probs = np.array(env.rules_move()); value=None; ... action = np.argmax(action_probs)
        # So it returns a distribution (likely deterministic).
        # We preserve original logic for 'rules' agent.
        
        self.print_top_actions(action_probs)
        if mask_invalid_actions:
             action_probs = mask_actions(env.legal_actions, action_probs)
             logger.debug('Masked ->')
             self.print_top_actions(action_probs)
        
        action = np.argmax(action_probs)
        if not choose_best_action:
             action = sample_action(action_probs)
        return action

      else:
        # Use SB3 predict with action_masks
        obs = env.observation
        masks = env.legal_actions if mask_invalid_actions else None
        
        try:
            # Try native MaskablePPO predict
            action, _state = self.model.predict(
                obs,
                deterministic=choose_best_action,
                action_masks=masks
            )
        except TypeError:
            # Fallback for standard PPO (does not support action_masks)
            # Use manual masking
            action_probs = get_action_probs_sb3(self.model, obs)
            
            if mask_invalid_actions:
                action_probs = mask_actions(env.legal_actions, action_probs)
            
            if choose_best_action:
                 action = np.argmax(action_probs)
            else:
                 action = sample_action(action_probs)
            
            logger.debug(f'Fallback action: {action}')
            return int(action)

        # predict returns a scalar or 0-d array for SingleEnv
        if isinstance(action, np.ndarray):
            action = action.item()
            
        logger.debug(f'Action chosen by model: {action}')
        return int(action)



