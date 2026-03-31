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

    def _op_attack_insurgent(self, s, u, a, b, target_type=None, removals_left=2, skip_roll=False, target_faction=None, is_ambush=False, ignore_bases_last=False, is_kidnap=False):
        sp = self.board.spaces[s]; cnt = int(sp.pieces[u] + sp.pieces[a])
        print(f"{'AMBUSH' if is_ambush else 'KIDNAP' if is_kidnap else 'ATTACK'} {sp.name} ({cnt})")
        if cnt <= 0 and not is_ambush:
            print(" -> No guerrilla to Attack.")
            return 0

        executing_faction = 1 if u == 2 else (2 if u == 5 else 3 if u == 8 else 0)

        if not skip_roll:
            if is_ambush or is_kidnap:
                # Rule 4.3.2/4.3.3: Ambush/Kidnap Activates 1 Underground Guerrilla only.
                if sp.pieces[u] > 0:
                    sp.pieces[u] -= 1
                    sp.pieces[a] += 1
                    self._move_cash_between_piece_indices(sp, u, a, 1)
            else:
                # Rule 3.3.3: "Activate all the executing Faction’s Guerrillas"
                revealed = int(sp.pieces[u])
                sp.pieces[u] = 0
                sp.pieces[a] += revealed
                if revealed > 0:
                    self._move_cash_between_piece_indices(sp, u, a, revealed)

            # Recalculate cnt after activation (for the roll check)
            cnt = int(sp.pieces[u] + sp.pieces[a])

            if is_ambush:
                roll = 1 # Automatic success
            else:
                is_m26 = (u == 2 and a == 3)
                roll = self._roll_die()
                if "Raul_Unshaded" in self.capabilities and is_m26 and roll > cnt:
                    print(f" -> Roll {roll} (FAIL) - Raúl reroll!")
                    roll = self._roll_die()

                if roll > cnt:
                    print(" -> Fail")
                    return 1

            if roll == 1 or is_ambush:
                print(f" -> Captured Goods ({'ambush' if is_ambush else 'roll 1'})")
                if self.players[executing_faction].available_forces[0] > 0:
                    sp.pieces[u] += 1
                    self.players[executing_faction].available_forces[0] -= 1

        killed_count = 0
        current_removals = removals_left

        def get_faction_pieces(f):
            if f == 0: return sp.pieces[0], sp.pieces[1], sp.govt_bases
            elif f == 1: return sp.pieces[2], sp.pieces[3], sp.pieces[4]
            elif f == 2: return sp.pieces[5], sp.pieces[6], sp.pieces[7]
            elif f == 3: return sp.pieces[8], sp.pieces[9], sp.pieces[10]
            return 0, 0, 0

        def get_eligible_types(f):
            ug, act, base = get_faction_pieces(f)
            el = []
            if ug > 0: el.append(0)
            if act > 0: el.append(1)

            if ignore_bases_last:
                if base > 0: el.append(2)
            else:
                if f == 3:
                    # "Attack cannot close Casinos if any Syndicate Guerrillas, Troops, or Police remain in the space"
                    if base > 0 and ug == 0 and act == 0 and sp.pieces[0] == 0 and sp.pieces[1] == 0:
                        el.append(2)
                else:
                    if base > 0 and ug == 0 and act == 0:
                        el.append(2)
            return el

        while current_removals > 0:
             enemy_factions = []
             for f in range(4):
                 if f == executing_faction: continue

                 # Pact of Caracas: 26July and DR cannot remove each other's pieces
                 if "PactOfCaracas_Unshaded" in self.capabilities:
                     if (executing_faction == 1 and f == 2) or (executing_faction == 2 and f == 1):
                         continue

                 if len(get_eligible_types(f)) > 0:
                     enemy_factions.append(f)

             if not enemy_factions:
                  break

             chosen_faction = target_faction
             target_faction = None

             if chosen_faction is None:
                  if len(enemy_factions) == 1:
                       chosen_faction = enemy_factions[0]
                  else:
                       self._pending_event_faction = {
                            "event": "OP_ATTACK",
                            "allowed": enemy_factions,
                            "removals_left": current_removals,
                            "space": s,
                            "u": u, "a": a, "b": b
                       }
                       self.phase = 6 # PHASE_CHOOSE_TARGET_FACTION
                       return None

             el = get_eligible_types(chosen_faction)
             if not el:
                  break

             chosen_type = target_type
             target_type = None

             if chosen_type is None:
                  if len(el) == 1:
                       chosen_type = el[0]
                  else:
                       self._pending_event_option = {
                            "event": "OP_ATTACK",
                            "allowed": el,
                            "removals_left": current_removals,
                            "space": s,
                            "u": u, "a": a, "b": b,
                            "target_faction": chosen_faction
                       }
                       self.phase = 7 # PHASE_CHOOSE_EVENT_OPTION
                       return None

             if chosen_faction == 0:
                  if chosen_type == 0:
                       self.board.remove_piece(s, 0, 0)
                       print(" -> Killed Troop")
                  elif chosen_type == 1:
                       self.board.remove_piece(s, 0, 1)
                       print(" -> Killed Police")
                  elif chosen_type == 2:
                       sp.govt_bases -= 1
                       self.players[0].available_bases += 1
                       sp.update_control()
                       print(" -> Killed Govt Base")
             else:
                  if chosen_type == 2 and chosen_faction == 3:
                       sp.pieces[10] -= 1
                       sp.closed_casinos += 1
                       sp.update_control()
                       print(" -> Closed Casino")
                  else:
                       self.board.remove_piece(s, chosen_faction, chosen_type)
                       piece_name = "UG" if chosen_type == 0 else "Active" if chosen_type == 1 else "Base"
                       print(f" -> Killed {piece_name} of faction {chosen_faction}")

             killed_count += 1
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

    def _op_terror_insurgent(self, s, u, a, is_kidnap=False):
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
            if not is_kidnap:
                sp.terror += 1
                if u == 2: # M26
                    _shift_alignment(sp, toward_active_opp=True)
                else: # DR or Syndicate
                    _shift_alignment(sp, toward_neutral=True)
        return 1

    def _op_rally_generic(self, s, u, a, b, f, sup, force_flip=False, ignore_choice=False):
        sp=self.board.spaces[s]; p=self.players[f]; print(f"{p.name}: RALLY {sp.name}")

        if force_flip:
             while sp.pieces[a]>0:
                sp.pieces[a]-=1
                sp.pieces[u]+=1
                self._move_cash_between_piece_indices(sp, a, u, 1)
             print(" -> Flipped")
             return 1

        can_loc=True
        if p.name=="DR": can_loc=(sp.type in [0,4] or sp.pieces[b]>0)

        cap = sp.population + sp.pieces[b]
        if p.name == "M26" and sp.pieces[b] > 0:
            cap = 2 * (sp.population + sp.pieces[b])

        if cap == 0 and sp.type in [1,3] and p.name=="M26": cap=1

        # If a base is present, choice is allowed between placing and flipping.
        has_base = (sp.pieces[b] > 0)
        has_active = (sp.pieces[a] > 0)

        # Syndicate: only place 1 piece (Rule 3.3.1)
        if p.name == "SYNDICATE":
            cap = 1

        can_place = (p.available_forces[sup] > 0 and cap > 0 and can_loc)

        if not ignore_choice and has_base and has_active and can_place:
            # Phase 7 choice needed
            self._pending_event_option = {
                "event": "OP_RALLY_CHOICE",
                "allowed": [0, 1], # 0=Place, 1=Flip
                "space": s,
                "u": u, "a": a, "b": b, "f": f, "sup": sup
            }
            self.phase = 7 # PHASE_CHOOSE_EVENT_OPTION
            return None

        if can_place:
            for _ in range(cap):
                if p.available_forces[sup]>0: sp.pieces[u]+=1; p.available_forces[sup]-=1
            print(f" -> Placed (Cap {cap})")
        elif has_active:
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

    def op_rally_m26(self, s, force_flip=False): return self._op_rally_generic(s,2,3,4,1,0, force_flip=force_flip)

    def op_ambush_m26(self, s):
        # Rule 4.3.2: automatically succeeds (2 removals), activate 1 UG, place 1 UG.
        # Bases Last restriction normally applies.
        return self._op_attack_insurgent(s, 2, 3, 4, skip_roll=False, is_ambush=True, ignore_bases_last=False)

    def op_kidnap_m26(self, s, target_faction=None):
        sp = self.board.spaces[s]
        # Only call Terror if it hasn't been called yet.
        # But wait, if we are resuming from Faction Selection, we shouldn't re-call Terror!
        if target_faction is None:
            self._op_terror_insurgent(s, 2, 3, is_kidnap=True)
            # Rule 4.3.3: Kidnap Activates 1 Underground Guerrilla.
            if sp.pieces[2] > 0:
                sp.pieces[2] -= 1
                sp.pieces[3] += 1
                self._move_cash_between_piece_indices(sp, 2, 3, 1)
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

            st = min(roll, self.players[target_faction].resources)
            self.players[target_faction].resources -= st
            self.players[1].resources += st
            print(f" -> M26 Kidnap: Took {st} Resources from {target_faction} (roll {roll})")

            if "Raul_Shaded" in self.capabilities:
                self.shift_aid(2 * int(st))

        if sp.pieces[10] > 0:
            sp.pieces[10] -= 1
            sp.closed_casinos += 1
            sp.update_control()
            print(" -> M26 Kidnap: Closed 1 Casino")

        return 0

    def op_rally_dr(self, s, force_flip=False): return self._op_rally_generic(s,5,6,7,2,0, force_flip=force_flip)

    def op_assassinate_dr(self, s):
        # Rule 4.4.3: remove or close ANY 1 enemy piece in a space selected for Terror.
        # The Terror operation itself is handled separately. This SA only performs the removal.
        print("DR: ASSASSINATE")
        return self._op_attack_insurgent(s, 5, 6, 7, removals_left=1, skip_roll=True, ignore_bases_last=True)

    def op_assassinate_hitmen(self, s):
        # Mafia Offensive capability: assassinate as if DR.
        print("SYN: HITMEN ASSASSINATE")
        return self._op_attack_insurgent(s, 8, 9, 10, removals_left=1, skip_roll=True, ignore_bases_last=True)

    def op_rally_syn(self, s, force_flip=False): return self._op_rally_generic(s,8,9,10,3,0, force_flip=force_flip)

    def op_bribe_syn(self, s):
        print("SYN: BRIBE"); st=min(2,self.players[0].resources)
        self.players[0].resources-=st; self.players[3].resources+=st; return 1

    def op_construct_syn(self, s):
        # Rule 3.3.5 Construct: Place a closed Casino or open a closed Casino. Cost 5 Resources.
        sp = self.board.spaces[s]
        print(f"SYN: CONSTRUCT {sp.name}")
        if sp.closed_casinos > 0:
            sp.closed_casinos -= 1
            sp.pieces[10] += 1
            print(" -> Opened closed Casino")
        elif self.players[3].available_bases > 0:
            sp.closed_casinos += 1
            self.players[3].available_bases -= 1
            print(" -> Placed closed Casino")
        sp.update_control()
        return 5