import re

with open("app/environments/cubalibre/envs/mixins/step.py", "r") as f:
    code = f.read()

# Re-insert the missing return blocks!
# The missing block was:
#                     player.eligible = False
#                     if not self.keep_eligible_this_action:
#                         self.ineligible_next_card.add(self.current_player_num)
#                     self.card_action_slot += 1
#                     self.phase = PHASE_CHOOSE_MAIN
#                     self._pending_main = None
#                     return self.observation, reward, done, False, {}

return_block = """
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}"""

# In DEFECTIONS_UN_PIECE
pattern = re.compile(r"""(                            self.phase = PHASE_CHOOSE_EVENT_OPTION\n                            advance_turn = False\n                            return self.observation, reward, done, False, \{\})\n(                elif event == "DEFECTIONS_UN_GOVT_REPLACE_CUBE":)""")
code = pattern.sub(r"\1" + return_block + r"\n\2", code)

# In DEFECTIONS_UN_GOVT_REPLACE_CUBE
pattern2 = re.compile(r"""(                            self.phase = PHASE_CHOOSE_EVENT_OPTION\n                            advance_turn = False\n                            return self.observation, reward, done, False, \{\})\n(                elif event == "ECHEVERRIA_SH_PIECE":)""")
code = pattern2.sub(r"\1" + return_block + r"\n\2", code)

# In ECHEVERRIA_SH_PIECE
pattern3 = re.compile(r"""(                    print\(f" -> Echeverría \(Sh\): Removed DR piece from \{sp\.name\} \(\{2 - remaining\}/2\)\."\)\n\n                    if remaining > 0:\n                        self\._pending_event_target = \{"event": "ECHEVERRIA_SH", "remaining": remaining\}\n                        self\.phase = PHASE_CHOOSE_TARGET_SPACE\n                        advance_turn = False\n                        return self\.observation, reward, done, False, \{\})\n(                elif event == "CHOMON_SH_PIECE":)""")
code = pattern3.sub(r"\1" + return_block + r"\n\2", code)

# In CHOMON_SH_ACTION
pattern4 = re.compile(r"""(                    else:\n                        print\(f" -> Fauré Chomón \(Sh\): Removed DR piece from \{sp\.name\}\."\))\n(                elif event == "MENOYO_UN_PIECE":)""")
code = pattern4.sub(r"\1" + return_block + r"\n\2", code)

# In MENOYO_UN_PIECE
pattern5 = re.compile(r"""(                        sp\.update_control\(\)\n                        print\(f" -> Eloy Gutiérrez Menoyo \(Un\): Replaced piece with 2 DR in \{sp\.name\}\."\))\n(                elif event == "MENOYO_SH_PIECE":)""")
code = pattern5.sub(r"\1" + return_block + r"\n\2", code)

# In MENOYO_SH_PIECE
pattern6 = re.compile(r"""(                    sp\.update_control\(\)\n                    print\(f" -> Eloy Gutiérrez Menoyo \(Sh\): Removed DR from \{sp\.name\}\."\))\n(                else:)""")
code = pattern6.sub(r"\1" + return_block + r"\n\2", code)


with open("app/environments/cubalibre/envs/mixins/step.py", "w") as f:
    f.write(code)

print("Restored returns!")
