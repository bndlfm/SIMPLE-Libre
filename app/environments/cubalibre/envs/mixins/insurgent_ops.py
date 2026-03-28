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

    def _op_attack_insurgent(self, s, u, a, b, target_type=None, removals_left=2, skip_roll=False, target_faction=None):
        sp = self.board.spaces[s]; cnt = int(sp.pieces[u] + sp.pieces[a])
        print(f"ATTACK {sp.name} ({cnt})")
        if cnt <= 0:
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
                print(" -> Fail")
                return 1

        killed_count = 0
        current_removals = removals_left

        executing_faction = 1 if u == 2 else (2 if u == 5 else 3 if u == 8 else 0)

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
        cap=sp.population+sp.pieces[b]
        if cap==0 and sp.type in [1,3] and p.name=="M26": cap=1
        if (p.available_forces[sup]>0) and cap>0 and can_loc:
            for _ in range(cap):
                if p.available_forces[sup]>0: sp.pieces[u]+=1; p.available_forces[sup]-=1
            print(f" -> Placed (Cap {cap})")
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

    def op_ambush_m26(self, s):
        sp = self.board.spaces[s]
        print(f"M26: AMBUSH {sp.name}")

        enemies = []
        if sp.pieces[0] + sp.pieces[1] + sp.govt_bases > 0:
            enemies.append(0)
        if sp.pieces[5] + sp.pieces[6] + sp.pieces[7] > 0:
            enemies.append(2)
        if sp.pieces[8] + sp.pieces[9] + sp.pieces[10] > 0:
            enemies.append(3)

        if not enemies:
            return 0

        if len(enemies) == 1:
            from app.environments.cubalibre.envs.constants import PHASE_CHOOSE_TARGET_PIECE
            self._pending_event_target = {
                "op": "AMBUSH_PIECE",
                "space": s,
                "ambushing_faction_id": 1,
                "target_faction_id": enemies[0]
            }
            self.phase = PHASE_CHOOSE_TARGET_PIECE
            return None
        else:
            from app.environments.cubalibre.envs.constants import PHASE_CHOOSE_TARGET_FACTION
            self._pending_event_faction = {
                "event": "AMBUSH_FACTION",
                "space": s,
                "ambushing_faction_id": 1,
                "allowed": enemies
            }
            self.phase = PHASE_CHOOSE_TARGET_FACTION
            return None

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

    def op_rally_dr(self, s): return self._op_rally_generic(s,5,6,7,2,0)

    def op_assassinate_dr(self, s):
        self._op_terror_insurgent(s,5,6); print("DR: ASSASSINATE"); sp=self.board.spaces[s]
        if sp.pieces[1]>0: sp.pieces[1]-=1
        elif sp.pieces[0]>0: sp.pieces[0]-=1
        return 1

    def op_assassinate_hitmen(self, s):
        self._op_terror_insurgent(s,8,9); print("SYN: HITMEN ASSASSINATE"); sp=self.board.spaces[s]
        if sp.pieces[1]>0: sp.pieces[1]-=1
        elif sp.pieces[0]>0: sp.pieces[0]-=1
        return 1

    def op_rally_syn(self, s): return self._op_rally_generic(s,8,9,10,3,0)

    def op_bribe_syn(self, s):
        print("SYN: BRIBE"); st=min(2,self.players[0].resources)
        self.players[0].resources-=st; self.players[3].resources+=st; return 1

    def op_construct_syn(self, s):
        print("SYN: CONSTRUCT"); self.board.spaces[s].pieces[10]+=1; self.players[3].available_bases-=1; return 1