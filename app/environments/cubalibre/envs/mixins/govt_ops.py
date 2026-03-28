import numpy as np
import random
import math
from collections import deque
from ..classes import *
from ..constants import *
from ..data import EVENT_DECK_DATA
from ..events import resolve_event, _free_ambush_against_govt, _free_ambush_against_govt_bases_first, _shift_alignment

class GovtOpsMixin:
    def _op_train_f_impl(self, s):
        p=self.players[0]; sp=self.board.spaces[s]; pl=0; print(f"GOVT: TRAIN {sp.name}")
        for _ in range(6):
            if p.available_forces[0]>0: self.board.add_piece(s,0,0); p.available_forces[0]-=1; pl+=1
            elif p.available_forces[1]>0: self.board.add_piece(s,0,1); p.available_forces[1]-=1; pl+=1
            else: break
        return self.get_govt_cost()

    def _op_train_b_impl(self, s):
        p=self.players[0]; sp=self.board.spaces[s]; print(f"GOVT: BASE {sp.name}"); rem=0
        while rem<2 and sp.pieces[1]>0: self.board.remove_piece(s,0,1); p.available_forces[1]+=1; rem+=1
        while rem<2 and sp.pieces[0]>0: self.board.remove_piece(s,0,0); p.available_forces[0]+=1; rem+=1
        sp.govt_bases+=1; p.available_bases-=1; return self.get_govt_cost()

    def _op_garrison_impl(self, s):
        sp=self.board.spaces[s]; print(f"GOVT: GARRISON {sp.name}")
        for adj in sp.adj_ids:
            mv = int(self.board.spaces[adj].pieces[1])
            if mv > 0:
                self._move_pieces_with_cash(adj, s, 0, 1, mv)
        return self.get_govt_cost()

    def _op_sweep_impl(self, s):
        sp=self.board.spaces[s]; print(f"GOVT: SWEEP {sp.name}")
        for adj in sp.adj_ids:
            mv = int(self.board.spaces[adj].pieces[0])
            if mv > 0:
                self._move_pieces_with_cash(adj, s, 0, 0, mv)

        # Capability: SIM (Police Move)
        if "SIM_Shaded" in self.capabilities:
            for adj in sp.adj_ids:
                mv = int(self.board.spaces[adj].pieces[1])
                if mv > 0:
                    self._move_pieces_with_cash(adj, s, 0, 1, mv)

        rev = 0
        cubes = int(sp.pieces[0]) + int(sp.pieces[1])
        # Forest space (type 1) halves cubes
        budget = (cubes // 2) if sp.type == 1 else cubes

        for idx in [2, 5, 8]:
            h = int(sp.pieces[idx])
            tr = min(h, budget)
            if tr > 0:
                sp.pieces[idx] -= tr
                sp.pieces[idx + 1] += tr
                rev += tr
                budget -= tr  # Consume budget
                self._move_cash_between_piece_indices(sp, idx, idx + 1, tr)
        print(f" -> Revealed {rev}")

        return self.get_govt_cost()


    def _op_assault_impl(self, s, target_faction=None, skip_armored_cars_redeploy=False, context="OP"):
        # 1. Determine Restrictions
        sp = self.board.spaces[s]
        is_restricted = (sp.type in [1, 3])
        if sp.type == 3 and "Mosquera_Shaded" in self.capabilities: is_restricted = False

        print(f"GOVT: ASSAULT {sp.name} {'(Limited)' if is_restricted else '(Full)'}")

        # Capability: Armored Cars (Move before Assault)
        if "ArmoredCars_Shaded" in self.capabilities and not skip_armored_cars_redeploy:
            for src in self.board.spaces:
                if int(src.id) == int(s):
                    continue
                mv = int(src.pieces[0])
                if mv > 0:
                    self._move_pieces_with_cash(int(src.id), int(s), 0, 0, mv)

        # 2. Define Killers
        sim = "SIM_Shaded" in self.capabilities
        troops = sp.pieces[0]
        police = sp.pieces[1]

        killers = troops + (police if sim else 0)
        u_killers = police + (troops if sim else 0)
        # Note: Even if they are Underground, they can be targeted if they are exposed.
        # But assault only naturally hits active or if police are present.
        # Wait, the rule is: ASSAULT: in each space, Troops and Police remove 1 Active Insurgent piece. Police may remove Underground.
        # But wait, if they are M26 Underground and there are NO Police, ASSAULT cannot hit them. Let's add Police to the space so the test makes sense, OR make the test expose them first (like SWEEP does).

        # 3. Identify Eligible Targets
        # Factions with pieces in the space.
        eligible = []
        # M26 (Idx 1): UG(2), Active(3), Base(4)
        if sp.pieces[3] > 0 or sp.pieces[4] > 0 or (sp.pieces[2] > 0 and u_killers > 0):
             eligible.append(1)
        # DR (Idx 2): UG(5), Active(6), Base(7)
        if sp.pieces[6] > 0 or sp.pieces[7] > 0 or (sp.pieces[5] > 0 and u_killers > 0):
             eligible.append(2)
        # Syn (Idx 3): UG(8), Active(9), Base(10)
        if sp.pieces[9] > 0 or sp.pieces[10] > 0 or (sp.pieces[8] > 0 and u_killers > 0):
             eligible.append(3)



        if not eligible:
            print(" -> No eligible targets for Assault.")
            return self.get_govt_cost()

        if target_faction is None:
            if len(eligible) > 1:
                # Multiple targets: Player must choose.
                self._pending_event_faction = {"event": "OP_ASSAULT", "allowed": eligible, "space": s, "context": context}
                return None
            else:
                target_faction = eligible[0]

        # 4. Execution
        f_idx = int(target_faction)
        if f_idx == 1:
            u, a, b = 2, 3, 4
        elif f_idx == 2:
            u, a, b = 5, 6, 7
        elif f_idx == 3:
            u, a, b = 8, 9, 10
        else:
             return self.get_govt_cost()

        killed = 0
        limit = 1 if is_restricted else 999

        idx_to_piece = {
            2: (1, 0), 3: (1, 1), 4: (1, 2),
            5: (2, 0), 6: (2, 1), 7: (2, 2),
            8: (3, 0), 9: (3, 1), 10: (3, 2),
        }
        def remove_insurgent_piece(piece_idx):
            faction_idx, piece_type = idx_to_piece[piece_idx]
            return self.board.remove_piece(s, faction_idx, piece_type)

        # Priority: Active -> Bases -> Underground

        # 1. Active (Killers only)
        # Note: Police only hit Underground (u_killers), so regular killers (Troops/SIM) hit Active/Base.
        if killers > 0 and killed < limit:
            while killers > 0 and sp.pieces[a] > 0 and killed < limit:
                remove_insurgent_piece(a)
                killers -= 1; killed += 1

        # 2. Bases (Killers only)
        if killers > 0 and killed < limit:
            while killers > 0 and sp.pieces[b] > 0 and killed < limit:
                remove_insurgent_piece(b)
                killers -= 1; killed += 1

        # 3. Underground (Police OR Killers)
        # Police hit Underground first? Or any?
        # Rules: "Police units... can Assault only against Underground Guerrillas."
        # Troops can assault anything.
        # Order: Active -> Base -> Underground.
        # So we use Troops for Active/Base first.
        # Now we are at Underground.
        # Use available Police (u_killers) first, then remaining Troops (killers).

        while u_killers > 0 and sp.pieces[u] > 0 and killed < limit:
            remove_insurgent_piece(u)
            u_killers -= 1; killed += 1

        if killers > 0 and killed < limit:
            while killers > 0 and sp.pieces[u] > 0 and killed < limit:
                remove_insurgent_piece(u)
                killers -= 1; killed += 1

        print(f" -> Killed {killed} ({self.factions_list[f_idx]})")

        if killed > 0:
            self._queue_cash_transfers_for_space(sp)

        return self.get_govt_cost()


    def op_transport(self, s):
        print(f"GOVT: TRANSPORT {self.board.spaces[s].name}")
        src = -1; mx = 0
        for sp in self.board.spaces:
            if sp.id!=s and sp.pieces[0]>mx: mx=sp.pieces[0]; src=sp.id
        if src!=-1:
            mv=min(3,mx);
            self._move_pieces_with_cash(src, s, 0, 0, mv)
        return 0

    def op_airstrike(self, s):
        sp=self.board.spaces[s]; print(f"GOVT: AIR STRIKE {sp.name}"); k=0
        limit = 2 if "Guantanamo_Shaded" in self.capabilities else 1
        for _ in range(limit):
            for idx in [4,7,10,3,6,9,2,5,8]:
                if sp.pieces[idx]>0:
                    faction_idx = 1 + ((idx - 2) // 3)
                    piece_type = (idx - 2) % 3
                    self.board.remove_piece(s, faction_idx, piece_type)
                    k+=1
                    break
        if k > 0:
            self._queue_cash_transfers_for_space(sp)
        print(f" -> Killed {k}"); return 0
