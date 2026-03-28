import sys
from sb3_contrib import MaskablePPO

try:
    model = MaskablePPO.load("zoo/cubalibre/base.zip")
    print("base Observation Space:", model.observation_space)
    print("base Action Space:", model.action_space)
except Exception as e:
    print("Could not load base:", e)

try:
    model2 = MaskablePPO.load("zoo/tmp/best_model.zip")
    print("best_model Observation Space:", model2.observation_space)
    print("best_model Action Space:", model2.action_space)
except Exception as e:
    print("Could not load best_model:", e)
