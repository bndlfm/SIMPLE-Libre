import sys
import os
import random

# Color codes for pretty printing
class Color:
    PURPLE = '\033[95m'; CYAN = '\033[96m'; GREEN = '\033[92m'; YELLOW = '\033[93m'; RED = '\033[91m'; BOLD = '\033[1m'; END = '\033[0m'

# Setup Path to find the 'cubalibre' package
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(root_dir)

from cubalibre.envs.env import CubaLibreEnv

# --- MAPPINGS FOR HUMAN INPUT ---
# Rows in our spreadsheet
OPS_GOVT = {
    0: "Train Force", 1: "Train Base", 2: "Garrison", 3: "Sweep",
    4: "Assault", 5: "Transport", 6: "Air Strike"
}

OPS_M26 = {
    7: "Rally", 8: "March", 9: "Attack", 10: "Terror"
}

# Columns in our spreadsheet (0-12)
SPACES = [
    "Pinar Del Rio", "Cigar EC", "La Habana", "Havana", "Matanzas",
    "Las Villas", "Textile EC", "Camaguey", "Camaguey City", "Oriente",
    "Sugar Cane EC", "Sierra Maestra", "Santiago De Cuba"
]

def print_math(op_id, space_id):
    """Shows the calculation converting Grid coordinates to Action ID"""
    total_spaces = 13
    action_id = (op_id * total_spaces) + space_id

    print(f"\n{Color.BOLD}--- THE MATH ---{Color.END}")
    print(f"Operation Index: {Color.CYAN}{op_id}{Color.END}")
    print(f"Space Index:     {Color.CYAN}{space_id}{Color.END}")
    print(f"Formula:         ({op_id} * {total_spaces}) + {space_id}")
    print(f"Action ID:       {Color.GREEN}{action_id}{Color.END}")
    return action_id

def main():
    print(f"{Color.BOLD}{Color.PURPLE}=== CUBA LIBRE: ACTION CALCULATOR ==={Color.END}")
    print("This tool maps your choices to the single integer the AI uses.")

    env = CubaLibreEnv(verbose=True, same_player_control=False)
    env.reset()
    env.render()

    while not env.done:
        current_player = env.players[env.current_player_num]

        if current_player.name == "GOVT":
            # --- HUMAN TURN ---
            print(f"\n{Color.BOLD}{Color.CYAN}>> YOUR TURN (GOVT){Color.END}")

            # 1. Select Operation (Row)
            print("Select Operation (The Row):")
            for k, v in OPS_GOVT.items(): print(f"  {k}: {v}")
            try:
                op_choice = int(input(f"{Color.YELLOW}Op ID > {Color.END}"))
                if op_choice not in OPS_GOVT: raise ValueError
            except ValueError: continue

            # 2. Select Space (Column)
            print("\nSelect Space (The Column):")
            for i, name in enumerate(SPACES): print(f"  {i}: {name}")
            try:
                space_choice = int(input(f"{Color.YELLOW}Space ID > {Color.END}"))
                if space_choice < 0 or space_choice > 12: raise ValueError
            except ValueError: continue

            # 3. Calculate and Execute
            action_id = print_math(op_choice, space_choice)

            print(f"\nExecuting Action ID: {Color.BOLD}{action_id}{Color.END}...")
            obs, reward, done, info = env.step(action_id)
            env.render()

        elif current_player.name == "M26":
            # --- BOT TURN ---
            print(f"\n{Color.BOLD}{Color.RED}>> BOT TURN (M26){Color.END}")

            # Simple Bot: Pick a legal action randomly
            legal_moves = env.legal_actions
            valid_indices = [i for i, x in enumerate(legal_moves) if x == 1]

            if not valid_indices:
                print("Bot has no legal moves (Pass).")
                env.current_player_num = (env.current_player_num + 1) % 4
                continue

            bot_action = random.choice(valid_indices)

            # Reverse Math to show what the bot did
            bot_op = bot_action // 13
            bot_space = bot_action % 13
            op_name = OPS_M26.get(bot_op, "Unknown")
            space_name = SPACES[bot_space]

            print(f"Bot selected Action ID: {Color.BOLD}{bot_action}{Color.END}")
            print(f"Math: {bot_action} / 13 = {bot_op} (Row), Remainder {bot_space} (Column)")
            print(f"Move: {Color.BOLD}{op_name}{Color.END} in {Color.BOLD}{space_name}{Color.END}")

            env.step(bot_action)
            env.render()

        else:
            # Skip DR/Syndicate for now
            print(f"\n{Color.CYAN}>> {current_player.name} PASSES (Not Implemented){Color.END}")
            env.current_player_num = (env.current_player_num + 1) % 4

if __name__ == "__main__":
    main()
