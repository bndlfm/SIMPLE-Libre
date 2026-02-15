import os
import logging
import numpy as np
import random

from utils.files import load_model, load_all_models, get_best_model_name
from utils.agents import Agent

import config

logger = logging.getLogger(__name__)

def selfplay_wrapper(env, env_kwargs=None):
    class SelfPlayEnv(env):
        # wrapper over the normal single player env, but loads the best self play model
        def __init__(self, opponent_type, verbose):
            kwargs = {} if env_kwargs is None else dict(env_kwargs)
            super(SelfPlayEnv, self).__init__(verbose, **kwargs)
            self.opponent_type = opponent_type
            self.opponent_models = load_all_models(self)
            self.best_model_name = get_best_model_name(self.name)

        def setup_opponents(self):
            if self.opponent_type == 'rules':
                self.opponent_agent = Agent('rules')
            else:
                # incremental load of new model
                best_model_name = get_best_model_name(self.name)
                if self.best_model_name != best_model_name:
                    self.opponent_models.append(load_model(self, best_model_name ))
                    self.best_model_name = best_model_name

                if self.opponent_type == 'random':
                    start = 0
                    end = len(self.opponent_models) - 1
                    i = random.randint(start, end)
                    self.opponent_agent = Agent('ppo_opponent', self.opponent_models[i]) 

                elif self.opponent_type == 'best':
                    self.opponent_agent = Agent('ppo_opponent', self.opponent_models[-1])  

                elif self.opponent_type == 'mostly_best':
                    j = random.uniform(0,1)
                    if j < 0.8:
                        self.opponent_agent = Agent('ppo_opponent', self.opponent_models[-1])  
                    else:
                        start = 0
                        end = len(self.opponent_models) - 1
                        i = random.randint(start, end)
                        self.opponent_agent = Agent('ppo_opponent', self.opponent_models[i])  

                elif self.opponent_type == 'base':
                    self.opponent_agent = Agent('base', self.opponent_models[0])  

            self.agent_player_num = np.random.choice(self.n_players)
            self.agents = [self.opponent_agent] * self.n_players
            self.agents[self.agent_player_num] = None
            try:
                #if self.players is defined on the base environment
                logger.debug(f'Agent plays as Player {self.players[self.agent_player_num].id}')
            except:
                pass


        def reset(self, *, seed=None, options=None):
            super(SelfPlayEnv, self).reset(seed=seed, options=options)
            self.setup_opponents()

            if self.current_player_num != self.agent_player_num:   
                self.continue_game()

            return self.observation, {}

        @property
        def current_agent(self):
            return self.agents[self.current_player_num]

        def continue_game(self):
            observation = None
            reward = None
            terminated = False
            truncated = False
            info = {}

            while self.current_player_num != self.agent_player_num:
                self.render()
                action = self.current_agent.choose_action(self, choose_best_action = False, mask_invalid_actions = True)
                observation, reward, terminated, truncated, info = super(SelfPlayEnv, self).step(action)
                done = terminated or truncated
                logger.debug(f'Rewards: {reward}')
                logger.debug(f'Done: {done}')
                if done:
                    break

            return observation, reward, terminated, truncated, info


        def step(self, action):
            self.render()
            observation, reward, terminated, truncated, info = super(SelfPlayEnv, self).step(action)
            done = terminated or truncated
            logger.debug(f'Action played by agent: {action}')
            logger.debug(f'Rewards: {reward}')
            logger.debug(f'Done: {done}')

            if not done:
                package = self.continue_game()
                if package[0] is not None:
                    observation, reward, terminated, truncated, info = package
                    done = terminated or truncated

            # Extract agent reward from per-player array.  The env may return:
            #   - info["rewards"] (list) on main exit paths
            #   - reward as a raw list on intermediate multi-step returns
            #   - reward as a scalar float
            rewards = info.get("rewards") if info else None
            if rewards is not None:
                agent_reward = float(rewards[self.agent_player_num])
            elif isinstance(reward, (list, tuple)):
                agent_reward = float(reward[self.agent_player_num])
            else:
                agent_reward = float(reward)
            logger.debug(f'\nReward To Agent: {agent_reward}')

            if done:
                self.render()

            return observation, agent_reward, terminated, truncated, {} 

    return SelfPlayEnv
