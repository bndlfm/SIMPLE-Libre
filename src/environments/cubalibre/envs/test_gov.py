import numpy as np
from cubalibre.envs.cubalibre import CubaLibreEnv

def test_govt_logic():
    print("Initializing Cuba Libre Environment...")
    env = CubaLibreEnv(verbose=True)
    env.reset()

    # --- TEST 1: TRAIN ---
    print("\n[TEST 1] Govt Trains in Havana (ID 3)")
    env.render()

    # Calculate Action ID: Op TRAIN(0) * 13 + Space HAVANA(3) = 3
    action_train = (0 * 13) + 3

    obs, reward, done, info = env.step(action_train)
    env.render()

    # Assertion: Havana (ID 3) should now have 1+3=4 Troops and 1+3=4 Police
    havana = env.board.spaces[3]
    print(f"Havana Troops: {havana.pieces[0]} (Expected 4)")
    print(f"Havana Police: {havana.pieces[1]} (Expected 4)")

    # --- TEST 2: GARRISON (MOVE) ---
    print("\n[TEST 2] Govt Garrisons La Habana (ID 2)")
    # Goal: Pull police from Havana (ID 3) into La Habana (ID 2).
    # Since Havana is adjacent to La Habana, this should work.

    # Force player back to GOVT for testing (ignoring rotation)
    env.current_player_num = 0
    env.players[0].eligible = True

    # Calculate Action ID: Op GARRISON(1) * 13 + Space LA_HABANA(2) = 15
    action_garrison = (1 * 13) + 2

    obs, reward, done, info = env.step(action_garrison)
    env.render()

    # Assertion:
    # La Habana (ID 2) should gain 1 Police.
    # Havana (ID 3) should lose 1 Police.
    la_habana = env.board.spaces[2]
    havana_after = env.board.spaces[3]

    print(f"La Habana Police: {la_habana.pieces[1]} (Expected 1)")
    print(f"Havana Police: {havana_after.pieces[1]} (Expected 3)")

if __name__ == "__main__":
    test_govt_logic()
