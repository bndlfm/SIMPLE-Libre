import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app.environments.cubalibre.envs.env import CubaLibreEnv

def setup_env():
    env = CubaLibreEnv()
    env.reset()
    # Clear all spaces first
    for space in env.board.spaces:
        for i in range(len(space.pieces)):
            space.pieces[i] = 0
    return env

def test_sweep_non_forest_limited_by_cubes():
    # Grass space (type 2) or City (type 0)
    # 1 Cube should only reveal 1 guerrilla, even if there are 3 hidden.
    env = setup_env()
    sp = env.board.spaces[2] # La Habana (Grass)
    assert sp.type == 2

    sp.pieces[0] = 1 # 1 Troop
    sp.pieces[2] = 3 # 3 Hidden M26

    env._op_sweep_impl(sp.id)

    assert sp.pieces[2] == 2, f"Expected 2 remain hidden, got {sp.pieces[2]}"
    assert sp.pieces[3] == 1, f"Expected 1 revealed, got {sp.pieces[3]}"

def test_sweep_budget_shared():
    # Grass space (type 2)
    # 2 Cubes total. 2 Hidden M26, 1 Hidden DR.
    # Total revealed should be exactly 2.
    env = setup_env()
    sp = env.board.spaces[2]

    sp.pieces[0] = 1 # 1 Troop
    sp.pieces[1] = 1 # 1 Police
    sp.pieces[2] = 2 # 2 Hidden M26
    sp.pieces[5] = 1 # 1 Hidden DR

    env._op_sweep_impl(sp.id)

    total_revealed = sp.pieces[3] + sp.pieces[6] + sp.pieces[9]
    assert total_revealed == 2, f"Expected 2 revealed, got {total_revealed}"

def test_sweep_forest_halves_cubes():
    # Forest space (type 1)
    # 3 Cubes should act as budget of 1 (3 // 2).
    # With 3 hidden guerrillas, only 1 should be revealed.
    env = setup_env()
    sp = env.board.spaces[0] # Pinar Del Rio (Forest)
    assert sp.type == 1

    sp.pieces[0] = 3 # 3 Troops
    sp.pieces[2] = 3 # 3 Hidden M26

    env._op_sweep_impl(sp.id)

    assert sp.pieces[3] == 1, "3 cubes in Forest should reveal 1 guerrilla"
    assert sp.pieces[2] == 2

def test_sweep_mountain_is_one_to_one():
    # Mountain space (type 3)
    # Mountain restricts Assault, but Sweep is 1-to-1!
    # 2 Cubes should reveal 2 guerrillas.
    env = setup_env()
    sp_id = next(s.id for s in env.board.spaces if s.type == 3)
    sp = env.board.spaces[sp_id]

    sp.pieces[0] = 2 # 2 Troops
    sp.pieces[2] = 3 # 3 Hidden M26

    env._op_sweep_impl(sp.id)

    assert sp.pieces[3] == 2, "2 cubes in Mountain should reveal 2 guerrillas"
    assert sp.pieces[2] == 1

if __name__ == "__main__":
    pytest.main([__file__])
