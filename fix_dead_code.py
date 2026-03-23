import re

# 1. Fix step.py duplicated block around line 3905-3912
with open("app/environments/cubalibre/envs/mixins/step.py", "r") as f:
    code = f.read()

# The duplicated block is:
#                     player.eligible = False
#                     if not self.keep_eligible_this_action:
#                         self.ineligible_next_card.add(self.current_player_num)
#                     self.card_action_slot += 1
#                     self.phase = PHASE_CHOOSE_MAIN
#                     self._pending_main = None
#                     return self.observation, reward, done, False, {}

dup_block = """                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}"""

# We look for two occurrences of this block back-to-back with some spacing
# Actually, the file has it right after another return statement
bad_code = """                    return self.observation, reward, done, False, {}

                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}"""

code = code.replace(bad_code, "                    return self.observation, reward, done, False, {}")

with open("app/environments/cubalibre/envs/mixins/step.py", "w") as f:
    f.write(code)

print("Fixed step.py")

# 2. Fix insurgent_ops.py LLM monologue dead code
with open("app/environments/cubalibre/envs/mixins/insurgent_ops.py", "r") as f:
    code = f.read()

# We want to keep everything up to "        return 1", then remove everything after that until "    def _op_mafia_attack"
match = re.search(r"        self\._queue_cash_transfers_for_space\(sp\)\n        return 1.*?(    def _op_mafia_attack)", code, re.DOTALL)
if match:
    clean_code = "        self._queue_cash_transfers_for_space(sp)\n        return 1\n\n" + match.group(1)
    code = code[:match.start()] + clean_code + code[match.end():]

    with open("app/environments/cubalibre/envs/mixins/insurgent_ops.py", "w") as f:
        f.write(code)
    print("Fixed insurgent_ops.py")
else:
    print("Could not find match in insurgent_ops.py")
