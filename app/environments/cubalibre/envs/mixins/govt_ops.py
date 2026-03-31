import numpy as np
from ..constants import *

class GovtOpsMixin:
    def _op_train_f_impl(self, s):
        p = self.players[0]
        sp = self.board.spaces[s]
        pl = 0
        print(f"GOVT: TRAIN {sp.name}")
        # Rule 3.2.1: Place up to 4 available cubes (deterministic priority: Troops then Police).
        for _ in range(4):
            if p.available_forces[0] > 0:
                self.board.add_piece(s, 0, 0)
                p.available_forces[0] -= 1
                pl += 1
            elif p.available_forces[1] > 0:
                self.board.add_piece(s, 0, 1)
                p.available_forces[1] -= 1
                pl += 1
            else:
                break
        sp.update_control()
        return self._maybe_offer_civic_action(s)

    def _op_train_b_impl(self, s):
        p = self.players[0]
        sp = self.board.spaces[s]
        print(f"GOVT: BASE {sp.name}")
        rem = 0
        # Rule 3.2.1: Replace 2 cubes with a Base.
        while rem < 2 and sp.pieces[1] > 0:
            self.board.remove_piece(s, 0, 1)
            p.available_forces[1] += 1
            rem += 1
        while rem < 2 and sp.pieces[0] > 0:
            self.board.remove_piece(s, 0, 0)
            p.available_forces[0] += 1
            rem += 1
        sp.govt_bases += 1
        p.available_bases -= 1
        sp.update_control()
        return self._maybe_offer_civic_action(s)

    def _op_garrison_impl(self, s, is_limited=False):
        sp = self.board.spaces[s]
        print(f"GOVT: GARRISON {sp.name}")
        # Rule 3.2.2: Move Police from adjacent spaces into EC/City.
        for adj in sp.adj_ids:
            mv = int(self.board.spaces[adj].pieces[1])
            if mv > 0:
                self._move_pieces_with_cash(adj, s, 0, 1, mv)
        sp.update_control()

        # Follow up: Free Assault in any one Garrison destination.
        enemies = sum(sp.pieces[2:11])
        if enemies > 0 and (sp.pieces[0] + sp.pieces[1]) > 0:
            self._pending_event_option = {
                "event": "OP_GARRISON_ASSAULT",
                "allowed": [0, 1], # 0=Skip, 1=Execute
                "targets": [s],
                "is_limited": is_limited
            }
            self.phase = PHASE_CHOOSE_EVENT_OPTION
            return None

        return self.get_govt_cost()

    def _op_sweep_impl(self, s):
        sp = self.board.spaces[s]
        print(f"GOVT: SWEEP {sp.name}")
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
        # Rule 3.2.3: In Forest, Activate only 1 Guerrilla for every 2 cubes.
        budget = (cubes // 2) if sp.type == 1 else cubes

        # Rule 4.2.2: Government may not target Syndicate pieces.
        for idx in [2, 5]:
            h = int(sp.pieces[idx])
            tr = min(h, budget)
            if tr > 0:
                sp.pieces[idx] -= tr
                sp.pieces[idx + 1] += tr
                rev += tr
                budget -= tr  # Consume budget
                self._move_cash_between_piece_indices(sp, idx, idx + 1, tr)
        print(f" -> Revealed {rev}")
        sp.update_control()
        return self.get_govt_cost()

    def _maybe_offer_civic_action(self, s):
        sp = self.board.spaces[s]
        # Rule 3.2.1: After Train, Govt may buy 1 Civic Action in any City or Govt-Base Province
        # that is Govt Controlled and has Troops AND Police.
        has_govt_control = (sp.controlled_by == 1)
        has_cubes = (sp.pieces[0] > 0 and sp.pieces[1] > 0)
        can_afford = (self.players[0].resources >= 4)

        if has_govt_control and has_cubes and can_afford:
            can_improve = (sp.terror > 0 or sp.alignment != 1 or not sp.support_active)
            if can_improve:
                self._pending_event_option = {
                    "event": "OP_TRAIN_CIVIC",
                    "allowed": [0, 1], # 0=Skip, 1=Execute
                    "space": s
                }
                self.phase = PHASE_CHOOSE_EVENT_OPTION
                return None
        return self.get_govt_cost()

    def _op_assault_impl(self, s, target_faction=None, skip_armored_cars_redeploy=False, context="OP"):
        sp = self.board.spaces[s]
        # Rule 3.2.4: In Mountain, remove only 1 piece for every 2 Troops.
        is_mountain = (sp.type == 3)
        if is_mountain and "Mosquera_Shaded" in self.capabilities:
            is_mountain = False

        print(f"GOVT: ASSAULT {sp.name}")

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
        troops = int(sp.pieces[0])
        police = int(sp.pieces[1])

        effective_troops = troops + (police if sim else 0)
        effective_police = 0 if sim else police

        # 3. Identify Eligible Targets
        # Rule 4.2.2: Government may not target Syndicate pieces.
        eligible = []
        # M26 (Idx 1): UG(2), Active(3), Base(4)
        if sp.pieces[3] > 0 or sp.pieces[4] > 0 or ((sp.type in [0, 4] or sim) and sp.pieces[2] > 0):
             eligible.append(1)
        # DR (Idx 2): UG(5), Active(6), Base(7)
        if sp.pieces[6] > 0 or sp.pieces[7] > 0 or ((sp.type in [0, 4] or sim) and sp.pieces[5] > 0):
             eligible.append(2)

        if not eligible:
            print(" -> No eligible targets for Assault.")
            return self.get_govt_cost()

        if target_faction is None:
            if len(eligible) > 1:
                # Multiple targets: Player must choose.
                self._pending_event_faction = {"event": "OP_ASSAULT", "allowed": eligible, "space": s, "context": context}
                self.phase = PHASE_CHOOSE_TARGET_FACTION
                return None
            else:
                target_faction = eligible[0]

        # 4. Execution
        f_idx = int(target_faction)
        u, a, b = (2, 3, 4) if f_idx == 1 else (5, 6, 7)

        # Kill limit
        limit = (effective_troops // 2) if is_mountain else effective_troops
        if sp.type in [0, 4]:
            limit += effective_police # 1 per Police bonus

        killed = 0
        idx_to_piece = {
            2: (1, 0), 3: (1, 1), 4: (1, 2),
            5: (2, 0), 6: (2, 1), 7: (2, 2),
        }
        def remove_insurgent_piece(piece_idx):
            faction_idx, piece_type = idx_to_piece[piece_idx]
            return self.board.remove_piece(s, faction_idx, piece_type)

        while killed < limit:
            # Priority: Active -> Underground (City/EC or SIM Shaded only) -> Bases
            # Bases Last: Targeted faction must have no Guerrillas (UG or Active).
            if sp.pieces[a] > 0:
                remove_insurgent_piece(a)
                killed += 1
            elif (sp.type in [0, 4] or sim) and sp.pieces[u] > 0:
                remove_insurgent_piece(u)
                killed += 1
            elif sp.pieces[a] == 0 and sp.pieces[u] == 0 and sp.pieces[b] > 0:
                remove_insurgent_piece(b)
                killed += 1
            else:
                break

        print(f" -> Killed {killed} ({self.factions_list[f_idx]})")
        if killed > 0:
            self._queue_cash_transfers_for_space(sp)

        return self.get_govt_cost()

    def op_transport(self, s):
        print(f"GOVT: TRANSPORT {self.board.spaces[s].name}")
        # Rule 4.2.1: Move up to 3 Troops from a City or Base to any 1 other space.
        src = -1
        mx = 0
        for sp in self.board.spaces:
            is_city_or_base = (sp.type == 0 or sp.govt_bases > 0)
            if sp.id != s and is_city_or_base and sp.pieces[0] > mx:
                mx = sp.pieces[0]
                src = sp.id
        if src != -1:
            mv = min(3, mx)
            self._move_pieces_with_cash(src, s, 0, 0, mv)
        return 0

    def op_airstrike(self, s):
        sp = self.board.spaces[s]
        print(f"GOVT: AIR STRIKE {sp.name}")
        k = 0
        limit = 2 if "Guantanamo_Shaded" in self.capabilities else 1
        # Rule 4.2.2: Cannot remove Syndicate pieces (indices 8,9,10).
        # Rule 4.2.2: "Remove 1 Active Guerrilla or, if the targeted Faction has no Guerrillas in the space, remove or close 1 of its Bases."
        # Deterministic priority: Active (3, 6) then Bases (4, 7). Underground (2, 5) are NOT eligible.
        for _ in range(limit):
            # Target Active first
            target_idx = -1
            if sp.pieces[3] > 0: target_idx = 3
            elif sp.pieces[6] > 0: target_idx = 6
            elif sp.pieces[4] > 0 and sp.pieces[2] == 0: target_idx = 4
            elif sp.pieces[7] > 0 and sp.pieces[5] == 0: target_idx = 7

            if target_idx != -1:
                faction_idx = 1 if target_idx in [2, 3, 4] else 2
                piece_type = (target_idx - 2) % 3 if faction_idx == 1 else (target_idx - 5) % 3
                self.board.remove_piece(s, faction_idx, piece_type)
                k += 1
            else:
                break
        if k > 0:
            self._queue_cash_transfers_for_space(sp)
        print(f" -> Killed {k}")
        return 0
