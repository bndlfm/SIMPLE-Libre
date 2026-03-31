import numpy as np
import random
import math
from collections import deque
from ..classes import *
from ..constants import *
from ..data import EVENT_DECK_DATA
from ..events import resolve_event, _free_ambush_against_govt, _free_ambush_against_govt_bases_first, _shift_alignment

class InsurgentOpsMixin:
    def _op_march_insurgent(self, s, u, a):
        sp=self.board.spaces[s]; print(f"MARCH {sp.name}")
        for adj in sp.adj_ids:
            n=self.board.spaces[adj]
            if n.pieces[a]>0:
                self._move_pieces_with_cash(adj, s, self.current_player_num, 1, 1)
            elif n.pieces[u]>0:
                moved = self._move_pieces_with_cash(adj, s, self.current_player_num, 0, 1)
                if moved > 0 and sp.type in [0, 4]:
                    sp.pieces[u] -= 1
                    sp.pieces[a] += 1
                    self._move_cash_between_piece_indices(sp, u, a, 1)
        return 1

    def _op_attack_insurgent(self, s, u, a, b, target_type=None, removals_left=2, skip_roll=False, target_faction=None, orig_event=None):
        sp = self.board.spaces[s]; cnt = int(sp.pieces[u] + sp.pieces[a])
        if target_faction is None and target_type is None:
            print(f"ATTACK {sp.name} ({cnt})")

        if cnt <= 0 and not skip_roll:
            print(" -> No guerrilla to Attack.")
            return 0

        if not skip_roll:
            revealed = min(int(sp.pieces[u]), 2)
            sp.pieces[u] -= revealed
            sp.pieces[a] += revealed
            if revealed > 0:
                self._move_cash_between_piece_indices(sp, u, a, revealed)

            is_m26 = (u == 2 and a == 3)
            roll = self._roll_die()
            if "Raul_Unshaded" in self.capabilities and is_m26 and roll > cnt:
                print(f" -> Roll {roll} (FAIL) - Raúl reroll!")
                roll = self._roll_die()

            if roll > cnt:
                print(f" -> Fail (Roll {roll} > Cnt {cnt})")
                return 1

        current_removals = removals_left
        executing_faction = 1 if u == 2 else (2 if u == 5 else 3 if u == 8 else 0)

        # Standard Attack (orig_event is None) uses priorities.
        # Ambush/Assassinate/Bribe (orig_event set) allows free choice.
        use_priority = (orig_event is None)

        def get_faction_pieces(f):
            if f == 0: return sp.pieces[0], sp.pieces[1], sp.govt_bases
            elif f == 1: return sp.pieces[2], sp.pieces[3], sp.pieces[4]
            elif f == 2: return sp.pieces[5], sp.pieces[6], sp.pieces[7]
            elif f == 3: return sp.pieces[8], sp.pieces[9], sp.pieces[10]
            return 0, 0, 0

        while current_removals > 0:
             eligible_targets = [] # list of (faction, type)

             if use_priority:
                 # Tier 1: Active/Cubes
                 for f in range(4):
                     if f == executing_faction: continue
                     ug, act, base = get_faction_pieces(f)
                     if f == 0:
                         if ug > 0: eligible_targets.append((0, 0)) # Troops
                         if act > 0: eligible_targets.append((0, 1)) # Police
                     else:
                         if act > 0: eligible_targets.append((f, 1))

                 if not eligible_targets:
                     # Tier 2: Bases/Casinos
                     for f in range(4):
                         if f == executing_faction: continue
                         ug, act, base = get_faction_pieces(f)
                         if base > 0:
                             if f == 3: # Casino protection
                                 if ug == 0 and act == 0 and sp.pieces[0] == 0 and sp.pieces[1] == 0:
                                     eligible_targets.append((3, 2))
                             else:
                                 eligible_targets.append((f, 2))

                 if not eligible_targets:
                     # Tier 3: Underground
                     for f in range(4):
                         if f == executing_faction: continue
                         if f == 0: continue # Govt has no UG
                         ug, act, base = get_faction_pieces(f)
                         if ug > 0: eligible_targets.append((f, 0))
             else:
                 # No priority: any enemy piece
                 for f in range(4):
                     if f == executing_faction: continue
                     ug, act, base = get_faction_pieces(f)
                     if f == 0:
                         if ug > 0: eligible_targets.append((0, 0)) # Troops
                         if act > 0: eligible_targets.append((0, 1)) # Police
                         if base > 0: eligible_targets.append((0, 2)) # Base
                     else:
                         if ug > 0: eligible_targets.append((f, 0))
                         if act > 0: eligible_targets.append((f, 1))
                         if base > 0:
                             if f == 3: # Casino protection
                                 if ug == 0 and act == 0 and sp.pieces[0] == 0 and sp.pieces[1] == 0:
                                     eligible_targets.append((3, 2))
                             else:
                                 eligible_targets.append((f, 2))

             if not eligible_targets:
                  break

             factions_in_tier = sorted(list(set(t[0] for t in eligible_targets)))
             chosen_faction = target_faction
             if chosen_faction is not None:
                  target_faction = None # Reset for next loop iteration

             if chosen_faction is None:
                  if len(factions_in_tier) == 1:
                       chosen_faction = factions_in_tier[0]
                  elif not self.manual:
                       # Default faction priority: Govt > M26 > DR > Syndicate (unless executing)
                       executing = 1 if u == 2 else (2 if u == 5 else 3 if u == 8 else 0)
                       priority = [0, 1, 2, 3]
                       if executing in priority:
                            priority.remove(executing)
                       for f_pref in priority:
                            if f_pref in factions_in_tier:
                                 chosen_faction = f_pref
                                 break
                  else:
                       self._pending_event_faction = {
                            "event": "OP_ATTACK",
                            "orig_event": orig_event,
                            "allowed": factions_in_tier,
                            "removals_left": current_removals,
                            "space": s,
                            "u": u, "a": a, "b": b
                       }
                       self.phase = 6 # PHASE_CHOOSE_TARGET_FACTION
                       return None

             if chosen_faction not in factions_in_tier:
                  break

             types_for_faction = sorted(list(set(t[1] for t in eligible_targets if t[0] == chosen_faction)))
             chosen_type = target_type
             if chosen_type is not None:
                  target_type = None # Reset for next loop iteration

             if chosen_type is None:
                  if len(types_for_faction) == 1:
                       chosen_type = types_for_faction[0]
                  elif not self.manual:
                       # Automated piece selection
                       if chosen_faction == 0:
                            # Govt: Police > Troops > Base
                            if 1 in types_for_faction: chosen_type = 1
                            elif 0 in types_for_faction: chosen_type = 0
                            else: chosen_type = 2
                       else:
                            # Insurgents: Active > Base > UG
                            if 1 in types_for_faction: chosen_type = 1
                            elif 2 in types_for_faction: chosen_type = 2
                            else: chosen_type = 0
                  else:
                       self._pending_event_option = {
                            "event": "OP_ATTACK",
                            "orig_event": orig_event,
                            "allowed": types_for_faction,
                            "removals_left": current_removals,
                            "space": s,
                            "u": u, "a": a, "b": b,
                            "target_faction": chosen_faction
                       }
                       self.phase = 7 # PHASE_CHOOSE_EVENT_OPTION
                       return None

             if int(chosen_faction) == 0:
                  if int(chosen_type) == 0:
                       self.board.remove_piece(s, 0, 0)
                       print(" -> Killed Troop")
                  elif int(chosen_type) == 1:
                       self.board.remove_piece(s, 0, 1)
                       print(" -> Killed Police")
                  elif int(chosen_type) == 2:
                       sp.govt_bases -= 1
                       self.players[0].available_bases += 1
                       sp.update_control()
                       print(" -> Killed Govt Base")
             else:
                  if int(chosen_type) == 2 and int(chosen_faction) == 3:
                       sp.pieces[10] -= 1
                       sp.closed_casinos += 1
                       sp.update_control()
                       print(" -> Closed Casino")
                  else:
                       self.board.remove_piece(s, int(chosen_faction), int(chosen_type))
                       piece_name = "UG" if int(chosen_type) == 0 else "Active" if int(chosen_type) == 1 else "Base"
                       print(f" -> Killed {piece_name} of faction {chosen_faction}")

             if orig_event == "OP_BRIBE_SYN":
                 self.players[int(chosen_faction)].resources = min(49, self.players[int(chosen_faction)].resources + 3)
                 print(f" -> Bribe: {self.players[int(chosen_faction)].name} gained 3 resources.")

             current_removals -= 1

        self._queue_cash_transfers_for_space(sp)
        return 1

    def _op_mafia_attack(self, s, u, a):
        sp = self.board.spaces[s]
        acting_cnt = int(sp.pieces[u] + sp.pieces[a])
        syn_cnt = int(sp.pieces[8] + sp.pieces[9])
        cnt = acting_cnt + min(1, syn_cnt)
        print(f"MAFIA ATTACK {sp.name} ({cnt})")
        if cnt <= 0:
            print(" -> No guerrilla to Attack.")
            return 0
        if acting_cnt > 0:
            revealed = min(int(sp.pieces[u]), 2)
            sp.pieces[u] -= revealed
            sp.pieces[a] += revealed
            if revealed > 0:
                self._move_cash_between_piece_indices(sp, u, a, revealed)
        elif sp.pieces[8] > 0:
            sp.pieces[8] -= 1
            sp.pieces[9] += 1
            self._move_cash_between_piece_indices(sp, 8, 9, 1)
        if self._roll_die()<=cnt:
            k=0
            for _ in range(2):
                if sp.pieces[1]>0: sp.pieces[1]-=1; k+=1
                elif sp.pieces[0]>0: sp.pieces[0]-=1; k+=1
                elif sp.govt_bases>0: sp.govt_bases-=1; k+=1
            print(f" -> Killed {k}")
        else: print(" -> Fail")
        return 1

    def _op_mafia_terror(self, s, acting_faction, u, a):
        sp = self.board.spaces[s]; print(f"MAFIA TERROR {sp.name}")
        if self._pact_blocks_opposition(acting_faction):
            print(" -> Pact of Caracas: Insurgent Terror blocked.")
            return 0
        if sp.pieces[u]>0:
            sp.pieces[u]-=1; sp.pieces[a]+=1
            self._move_cash_between_piece_indices(sp, u, a, 1)
        elif sp.pieces[8]>0:
            sp.pieces[8]-=1; sp.pieces[9]+=1
            self._move_cash_between_piece_indices(sp, 8, 9, 1)
        sp.terror+=1;
        if sp.alignment==1: sp.alignment=0
        return 1

    def _op_terror_insurgent(self, s, u, a):
        sp=self.board.spaces[s]; print(f"TERROR {sp.name}")
        if self._pact_blocks_opposition(self.current_player_num):
            print(" -> Pact of Caracas: Insurgent Terror blocked.")
            return 0
        if sp.pieces[u]>0:
            sp.pieces[u]-=1; sp.pieces[a]+=1
            self._move_cash_between_piece_indices(sp, u, a, 1)

        if sp.type == 4: # Economic Center
            if not sp.sabotage:
                sp.sabotage = True
        else:
            sp.terror += 1
            if u == 2: # M26
                _shift_alignment(sp, toward_active_opp=True)
            else: # DR or Syndicate
                _shift_alignment(sp, toward_neutral=True)
        return 1

    def _op_rally_generic(self, s, u, a, b, f, sup):
        sp=self.board.spaces[s]; p=self.players[f]; print(f"{p.name}: RALLY {sp.name}")
        can_loc=True
        if p.name=="DR": can_loc=(sp.type in [0,4] or sp.pieces[b]>0)

        # Rule 3.3.1: Rally Capacities
        if p.name == "M26":
            cap = 2 * (int(sp.population) + int(sp.pieces[b]))
            if cap == 0 and sp.type in [1, 3]: cap = 1
        elif p.name == "SYNDICATE":
            cap = 1 # Single guerrilla
        else:
            cap = int(sp.population) + int(sp.pieces[b])

        if (p.available_forces[sup]>0) and cap>0 and can_loc:
            placed = 0
            for _ in range(cap):
                if p.available_forces[sup]>0:
                    sp.pieces[u]+=1; p.available_forces[sup]-=1
                    placed += 1
            print(f" -> Placed {placed} (Cap {cap})")
        else:
            while sp.pieces[a]>0:
                sp.pieces[a]-=1
                sp.pieces[u]+=1
                self._move_cash_between_piece_indices(sp, a, u, 1)
            print(" -> Flipped")
        if p.name=="M26" and "GuerrillaLife_Unshaded" in self.capabilities and sp.pieces[a] > 0:
            moved = int(sp.pieces[a])
            sp.pieces[u] += moved
            sp.pieces[a] = 0
            self._move_cash_between_piece_indices(sp, a, u, moved)
        return 1

    # Delegates

    def op_rally_m26(self, s): return self._op_rally_generic(s,2,3,4,1,0)

    def op_ambush_m26(self, s, target_type=None, removals_left=2, target_faction=None):
        sp = self.board.spaces[s]
        # Ambush rule 4.3.2: remove 2 enemy pieces (automatic success),
        # AND add an available guerrilla (Underground).
        res = self._op_attack_insurgent(s, 2, 3, 4, target_type=target_type, removals_left=removals_left, skip_roll=True, target_faction=target_faction, orig_event="OP_AMBUSH_M26")
        if res is None:
            return None # Still selecting targets

        # Attack logic handles removal. Now add the guerrilla if it was the start of the action.
        # We only add it when we are NOT resuming (target_faction is None)
        if target_faction is None and target_type is None:
            if self.players[1].available_forces[0] > 0:
                sp.pieces[2] += 1
                self.players[1].available_forces[0] -= 1
                print(" -> M26 Ambush: Added UG Guerrilla.")
            sp.update_control()
        return 1

    def op_ambush_dr(self, s, target_type=None, removals_left=2, target_faction=None):
        sp = self.board.spaces[s]
        # Rule 4.4.2: same as M26 but DR pieces.
        res = self._op_attack_insurgent(s, 5, 6, 7, target_type=target_type, removals_left=removals_left, skip_roll=True, target_faction=target_faction, orig_event="OP_AMBUSH_DR")
        if res is None:
            return None
        if target_faction is None and target_type is None:
            if self.players[2].available_forces[0] > 0:
                sp.pieces[5] += 1
                self.players[2].available_forces[0] -= 1
                print(" -> DR Ambush: Added UG Guerrilla.")
            sp.update_control()
        return 1

    def op_kidnap_m26(self, s, target_faction=None):
        sp = self.board.spaces[s]
        # Only call Terror if it hasn't been called yet.
        # But wait, if we are resuming from Faction Selection, we shouldn't re-call Terror!
        if target_faction is None:
            self._op_terror_insurgent(s, 2, 3)
            print("M26: KIDNAP")

            allowed_factions = []
            if sp.type in [0, 4]: # City or EC
                allowed_factions.append(0) # Govt
            if sp.pieces[10] > 0: # Open Casino
                allowed_factions.append(3) # Syndicate

            if not allowed_factions:
                return 0

            if len(allowed_factions) == 1:
                target_faction = allowed_factions[0]
            else:
                self._pending_event_faction = {
                    "event": "OP_KIDNAP",
                    "allowed": allowed_factions,
                    "space": s
                }
                self.phase = 6 # PHASE_CHOOSE_TARGET_FACTION
                return None

        # Resolve Kidnap against target_faction
        has_cash = False
        cash_holders = self._cash_piece_indices_for_faction(target_faction)
        for h in cash_holders:
            if sp.cash_holders[h] > 0:
                has_cash = True
                sp.cash_holders[h] -= 1
                sp.cash_holders[3] += 1 # Give to Active M26
                sp.refresh_cash_counts()
                print(f" -> M26 Kidnap: Took Cash from {target_faction}")
                break

        if not has_cash:
            roll = self._roll_die()
            if "Raul_Unshaded" in self.capabilities and roll <= 3:
                # Assuming Raul unshaded rerolls Kidnap?
                # "26July may reroll each Attack or Kidnap"
                # If roll is low, might reroll for higher resources?
                # For simplicity, if roll < 4, reroll once.
                roll2 = self._roll_die()
                if roll2 > roll: roll = roll2

            st = min(roll, int(self.players[target_faction].resources))
            self.players[target_faction].resources = int(self.players[target_faction].resources) - st
            self.players[1].resources = int(self.players[1].resources) + st
            print(f" -> M26 Kidnap: Took {st} Resources from {target_faction} (roll {roll})")

            if "Raul_Shaded" in self.capabilities:
                self.set_aid(int(self.aid) + 2 * st)

        if sp.pieces[10] > 0:
            sp.pieces[10] -= 1
            sp.closed_casinos += 1
            sp.update_control()
            print(" -> M26 Kidnap: Closed 1 Casino")

        return 0

    def op_rally_dr(self, s): return self._op_rally_generic(s,5,6,7,2,0)

    def op_assassinate_dr(self, s, target_type=None, target_faction=None):
        # Assassinate Rule 4.4.3: removes ANY 1 enemy piece.
        if target_faction is None and target_type is None:
            self._op_terror_insurgent(s, 5, 6)
            print("DR: ASSASSINATE")

        res = self._op_attack_insurgent(s, 5, 6, 7, target_type=target_type, removals_left=1, skip_roll=True, target_faction=target_faction, orig_event="OP_ASSASSINATE_DR")
        return res

    def op_assassinate_hitmen(self, s, target_type=None, target_faction=None):
        if target_faction is None and target_type is None:
            self._op_terror_insurgent(s, 8, 9)
            print("SYN: HITMEN ASSASSINATE")

        res = self._op_attack_insurgent(s, 8, 9, 10, target_type=target_type, removals_left=1, skip_roll=True, target_faction=target_faction, orig_event="OP_ASSASSINATE_HITMEN")
        return res

    def op_rally_syn(self, s): return self._op_rally_generic(s,8,9,10,3,0)

    def op_bribe_syn(self, s, target_type=None, target_faction=None):
        # Rule 4.5.4: Bribe removes or flips pieces at cost of 3 resources.
        # "Remove up to 2 cubes, remove or flip up to 2 Guerrillas, or remove an enemy Base."
        if target_faction is None and target_type is None:
            print("SYN: BRIBE")

        res = self._op_attack_insurgent(s, 8, 9, 10, target_type=target_type, removals_left=2, skip_roll=True, target_faction=target_faction, orig_event="OP_BRIBE_SYN")
        if res is not None:
            return 3 # Cost is 3
        return None

    def op_construct_syn(self, s):
        print("SYN: CONSTRUCT"); self.board.spaces[s].pieces[10]+=1; self.players[3].available_bases-=1; return 1