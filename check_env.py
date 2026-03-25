from environments.cubalibre.envs.env import CubaLibreEnv

env = CubaLibreEnv()
print("Env Observation Space:", env.observation_space)
print("Env Action Space:", env.action_space)
