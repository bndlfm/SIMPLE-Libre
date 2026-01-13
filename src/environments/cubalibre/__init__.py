from gym.envs.registration import register

register(
    id='CubaLibre-v0',
    entry_point='cubalibre.envs:CubaLibreEnv',
)

