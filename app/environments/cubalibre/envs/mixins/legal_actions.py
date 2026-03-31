import numpy as np
import random
import math
from collections import deque
from ..classes import *
from ..constants import *
from ..data import EVENT_DECK_DATA
from ..events import resolve_event, _free_ambush_against_govt, _free_ambush_against_govt_bases_first, _shift_alignment

class LegalActionsMixin:
    @property
    def legal_actions(self):
        mask = np.zeros(self.action_space.n)
        player = self.players[self.current_player_num]
        if self.phase == PHASE_CHOOSE_MAIN and not player.eligible:
            return mask

        # Phase 0: choose Pass vs Event vs Ops
        if self.phase == PHASE_CHOOSE_MAIN:
            mask[self._main_action_base + MAIN_PASS] = 1
            if self.card_action_slot == 0:
                mask[self._main_action_base + MAIN_EVENT] = 1
                mask[self._main_action_base + MAIN_OPS] = 1
            else:
                first_action = self.card_first_action
                if first_action == "EVENT":
                    mask[self._limited_main_action_id] = 1
                elif first_action == "OPS":
                    mask[self._main_action_base + MAIN_EVENT] = 1
                    mask[self._limited_main_action_id] = 1
                elif first_action == "PASS" or first_action == "ILLEGAL":
                    mask[self._main_action_base + MAIN_EVENT] = 1
                    mask[self._main_action_base + MAIN_OPS] = 1
                else:
                    mask[self._limited_main_action_id] = 1
            return mask

        if self.phase == PHASE_PROPAGANDA_REDEPLOY_MENU:
            police_sources = self._propaganda_redeploy_police_sources()
            mandatory_sources = self._propaganda_redeploy_troop_mandatory_sources()
            optional_sources = self._propaganda_redeploy_troop_optional_sources()
            if not mandatory_sources:
                mask[self._main_action_base + MAIN_PASS] = 1
            if police_sources and self._propaganda_redeploy_police_destinations():
                mask[self._main_action_base + MAIN_EVENT] = 1
            if mandatory_sources or optional_sources:
                mask[self._main_action_base + MAIN_OPS] = 1
            return mask

        # Phase 1: choose Event side
        if self.phase == PHASE_CHOOSE_EVENT_SIDE:
            # If a side has blank text in data.py, treat as not selectable.
            try:
                card_data = EVENT_DECK_DATA.get(self.current_card.id)
            except Exception:
                card_data = None

            if card_data is None:
                # Fallback: allow both
                mask[self._event_side_base + EVENT_UNSHADED] = 1
                mask[self._event_side_base + EVENT_SHADED] = 1
                return mask

            unshaded = (card_data.get('unshaded') or '').strip()
            shaded = (card_data.get('shaded') or '').strip()
            if unshaded:
                mask[self._event_side_base + EVENT_UNSHADED] = 1
            if shaded:
                mask[self._event_side_base + EVENT_SHADED] = 1
            return mask

        # Phase 5: choose a target space (event-driven)
        if self.phase == PHASE_CHOOSE_TARGET_SPACE:
            target_mask = np.zeros(self._target_space_action_count)
            if self._pending_launder is not None and self._pending_launder.get("stage") == "SPACE":
                provider = int(self._pending_launder.get("provider"))
                for s_id in self._launder_cash_spaces(provider):
                    target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "CIVIC_ACTION":
                mask[self._main_action_base + MAIN_PASS] = 1
                for s_id in self._propaganda_civic_action_targets():
                    target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_POLICE_SRC":
                mask[self._main_action_base + MAIN_PASS] = 1
                for s_id in self._propaganda_redeploy_police_sources():
                    target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_POLICE_DEST":
                src = int(self._pending_propaganda.get("src"))
                for s_id in self._propaganda_redeploy_police_destinations():
                    if s_id != src:
                        target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_TROOPS_MANDATORY_SRC":
                for s_id in self._propaganda_redeploy_troop_mandatory_sources():
                    target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_TROOPS_MANDATORY_DEST":
                src = int(self._pending_propaganda.get("src"))
                for s_id in self._propaganda_redeploy_troop_destinations():
                    if s_id != src:
                        target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_TROOPS_OPTIONAL_SRC":
                mask[self._main_action_base + MAIN_PASS] = 1
                for s_id in self._propaganda_redeploy_troop_optional_sources():
                    target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_TROOPS_OPTIONAL_DEST":
                src = int(self._pending_propaganda.get("src"))
                for s_id in self._propaganda_redeploy_troop_destinations():
                    if s_id != src:
                        target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "AGITATION":
                mask[self._main_action_base + MAIN_PASS] = 1
                for s_id in self._propaganda_agitation_targets():
                    target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "EXPAT_BACKING":
                mask[self._main_action_base + MAIN_PASS] = 1
                for s_id in self._propaganda_expat_targets():
                    target_mask[s_id] = 1
                mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
                return mask
            pending = self._pending_event_target
            pending_op = self._pending_op_target
            if pending is None and pending_op is None:
                return mask

            event = None if pending is None else pending.get("event")
            faction = None if pending is None else pending.get("faction")
            op_kind = None if pending_op is None else pending_op.get("op")

            for s_id in range(self.num_spaces):
                sp = self.board.spaces[s_id]
                if event == "REBEL_AIR_FORCE_UN" and faction in ["M26", "DR"]:
                    has_govt = (sp.pieces[0] + sp.pieces[1] + sp.govt_bases) > 0
                    if not has_govt:
                        continue
                    if faction == "M26":
                        u, a = 2, 3
                    else:
                        u, a = 5, 6
                    if (sp.pieces[u] + sp.pieces[a]) > 0:
                        target_mask[s_id] = 1
                elif event == "FAT_BUTCHER_SH":
                    stage = pending.get("stage", "AMBUSH")
                    if stage == "AMBUSH":
                        has_govt = (sp.pieces[0] + sp.pieces[1] + sp.govt_bases) > 0
                        if not has_govt:
                            continue
                        if (sp.pieces[8] + sp.pieces[9]) > 0:
                            target_mask[s_id] = 1
                    else:
                        # Stage OPEN: choose where to open a closed casino.
                        if getattr(sp, "closed_casinos", 0) > 0:
                            target_mask[s_id] = 1
                elif event == "MAP_UN":
                    if (sp.pieces[0] + sp.pieces[1]) > 0:
                        target_mask[s_id] = 1
                elif event == "LLANO_UN":
                    if sp.type == 0:
                        target_mask[s_id] = 1
                elif event == "LLANO_SH":
                    if sp.type == 0:
                        target_mask[s_id] = 1
                elif event == "GENERAL_STRIKE_SH":
                    stage = pending.get("stage", "TARGET")
                    if stage == "TARGET":
                        if sp.type == 0:
                            target_mask[s_id] = 1
                    elif stage == "OPEN":
                        if int(getattr(sp, "closed_casinos", 0)) > 0:
                            target_mask[s_id] = 1
                elif event == "SIM_UN":
                    # S.I.M (Un): Remove Support from a space with no Police.
                    if int(sp.alignment) == 1 and int(sp.pieces[1]) == 0:
                        target_mask[s_id] = 1
                elif event == "ELECTION_SH":
                    # Election (Sh): Set a City to Neutral. Aid +10.
                    if sp.type == 0:
                        target_mask[s_id] = 1
                elif event == "ARMORED_CARS_UN" and faction in ["M26", "DR"]:
                    stage = pending.get("stage", "TARGET")
                    if stage == "TARGET":
                        if faction == "M26":
                            u, a = 2, 3
                        else:
                            u, a = 5, 6

                        has_adj = any((self.board.spaces[i].pieces[u] + self.board.spaces[i].pieces[a]) > 0 for i in sp.adj_ids)
                        if has_adj:
                            target_mask[s_id] = 1
                    else:
                        dest = pending.get("dest")
                        if dest is None:
                            continue
                        if s_id not in self.board.spaces[dest].adj_ids:
                            continue
                        if faction == "M26":
                            u, a = 2, 3
                        else:
                            u, a = 5, 6
                        if (sp.pieces[u] + sp.pieces[a]) > 0:
                            target_mask[s_id] = 1
                elif event == "FAT_BUTCHER_UN":
                    if sp.pieces[10] > 0:
                        target_mask[s_id] = 1

                elif event == "FANGIO_SH":
                    stage = pending.get("stage", "SPACE1")
                    picked = pending.get("picked") or []
                    if s_id in picked:
                        continue
                    has_any_casino = (sp.pieces[10] > 0) or (getattr(sp, "closed_casinos", 0) > 0)
                    if has_any_casino:
                        target_mask[s_id] = 1

                elif event == "CANTILLO_UN":
                    stage = pending.get("stage", "SPACE")
                    if stage == "SPACE":
                        has_troops = int(sp.pieces[0]) > 0
                        has_any_g = int(sp.pieces[2] + sp.pieces[3] + sp.pieces[5] + sp.pieces[6] + sp.pieces[8] + sp.pieces[9]) > 0
                        if has_troops and has_any_g:
                            target_mask[s_id] = 1
                    elif stage == "MOVE":
                        src = pending.get("src")
                        faction = pending.get("faction")
                        # Only allow PASS when all guerrillas have marched out
                        if src is not None and faction is not None:
                            src_sp_chk = self.board.spaces[int(src)]
                            if faction == "M26":
                                u_chk, a_chk = 2, 3
                            elif faction == "DR":
                                u_chk, a_chk = 5, 6
                            else:
                                u_chk, a_chk = 8, 9
                            if int(src_sp_chk.pieces[u_chk] + src_sp_chk.pieces[a_chk]) == 0:
                                mask[self._main_action_base + MAIN_PASS] = 1
                        src = pending.get("src")
                        faction = pending.get("faction")
                        if src is None or faction is None:
                            continue
                        if s_id == src:
                            continue
                        if s_id not in self.board.spaces[int(src)].adj_ids:
                            continue
                        src_sp = self.board.spaces[int(src)]
                        if faction == "M26":
                            u, a = 2, 3
                        elif faction == "DR":
                            u, a = 5, 6
                        else:
                            u, a = 8, 9
                        if int(src_sp.pieces[u] + src_sp.pieces[a]) > 0:
                            target_mask[s_id] = 1
                elif event == "CANTILLO_SH":
                    # Province or City with Troops.
                    if sp.type in [0, 1, 2, 4] and int(sp.pieces[0]) > 0: # 0:City, 1,2:Prov, 4:Econ
                        target_mask[s_id] = 1
                elif event == "SIM_UN":
                    # Support, No Police.
                    if sp.alignment == 1 and int(sp.pieces[1]) == 0:
                        target_mask[s_id] = 1
                elif event == "MASFERRER_UN":
                    stage = pending.get("stage", "SPACE1")
                    if stage == "SPACE1":
                        if sp.type in [1, 2, 3] and int(sp.pieces[0]) > 0:
                            target_mask[s_id] = 1
                    elif stage == "SPACE2":
                        src = pending.get("src")
                        if sp.type in [1, 2, 3] and src is not None and s_id in self.board.spaces[src].adj_ids:
                            target_mask[s_id] = 1
                elif event == "GENERAL_STRIKE_SH":
                    stage = pending.get("stage", "TARGET")
                    if stage == "TARGET":
                        # City.
                        if sp.type == 0:
                            target_mask[s_id] = 1
                    elif stage == "OPEN":
                        if int(getattr(sp, "closed_casinos", 0)) > 0:
                            target_mask[s_id] = 1
                elif event == "MAP_UN":
                    # Has cubes.
                    if int(sp.pieces[0] + sp.pieces[1]) > 0:
                        target_mask[s_id] = 1
                elif event == "BATISTA_FLEES_UN":
                    # Has Troops.
                    if int(sp.pieces[0]) > 0:
                        target_mask[s_id] = 1
                elif event == "LARRAZABAL_SH":
                    # Has M26 Base.
                    if int(sp.pieces[4]) > 0:
                        target_mask[s_id] = 1
                elif event == "LARRAZABAL_UN":
                    # Has any 26July piece (guerrilla or base).
                    if int(sp.pieces[2] + sp.pieces[3] + sp.pieces[4]) > 0:
                        target_mask[s_id] = 1
                elif event == "MOSQUERA_UN":
                    # Sanchez Mosquera (Un): Remove all Troops from a Mountain space.
                    if sp.type == 3 and int(sp.pieces[0]) > 0:
                        target_mask[s_id] = 1
                elif event == "BRAC_UN":
                    # BRAC (Un): Remove any 2 Guerrillas.
                    if any(int(sp.pieces[idx]) > 0 for idx in [2, 3, 5, 6, 8, 9]):
                        target_mask[s_id] = 1
                elif event == "BRAC_SH":
                    target_mask[s_id] = 1
                elif event == "COME_COMRADES_UN":
                    # Place 3 M26 Guerrillas anywhere.
                    target_mask[s_id] = 1
                elif event == "CARLOS_PRIO_SH":
                    # Place DR Base in space without Govt Control.
                    if int(self.players[2].available_bases) > 0 and sp.controlled_by != 1:
                        target_mask[s_id] = 1
                elif event == "THE_TWELVE_UN_DEST":
                    # March destination (DEST) or source (SRC).
                    stage = pending.get("stage", "DEST")
                    faction = pending.get("faction")
                    if faction == "M26": u, a = 2, 3
                    else: u, a = 5, 6
                    if stage == "DEST":
                        if faction == "DR" and "Morgan_Unshaded" in self.capabilities:
                            if self._has_guerrillas_within_range(s_id, u, a, 2):
                                target_mask[s_id] = 1
                        else:
                            has_adj_pieces = any((self.board.spaces[adj_id].pieces[u] + self.board.spaces[adj_id].pieces[a]) > 0 for adj_id in sp.adj_ids)
                            if has_adj_pieces:
                                target_mask[s_id] = 1
                    else:
                        dest = pending.get("dest")
                        if dest is None:
                            continue
                        if faction == "DR" and "Morgan_Unshaded" in self.capabilities:
                            dist = self._shortest_space_distances(dest)
                            if dist.get(s_id, 999) <= 2 and (sp.pieces[u] + sp.pieces[a]) > 0:
                                target_mask[s_id] = 1
                        else:
                            if s_id in self.board.spaces[dest].adj_ids and (sp.pieces[u] + sp.pieces[a]) > 0:
                                target_mask[s_id] = 1

                elif event == "FANGIO_UN":
                    if sp.type == 0: # City
                        target_mask[s_id] = 1
                elif event == "RADIO_REBELDE_UN":
                    if sp.type in [1, 2, 3]: # Province
                        picked = pending.get("picked", [])
                        if s_id not in picked:
                            target_mask[s_id] = 1
                elif event == "RADIO_REBELDE_SH":
                    if sp.type in [1, 2, 3] and int(sp.pieces[4]) > 0: # Province with M26 Base
                        target_mask[s_id] = 1
                elif event == "VILMA_ESPIN_UN":
                    # Sierra Maestra (11) or adjacent
                    if s_id == 11 or s_id in self.board.spaces[11].adj_ids:
                        target_mask[s_id] = 1
                elif event == "VILMA_ESPIN_SH":
                    # City other than Havana (3)
                    if sp.type == 0 and s_id != 3:
                        target_mask[s_id] = 1
                elif event == "ESCAPADE_UN":
                    # Camaguey (7) or Oriente (9)
                    if s_id in [7, 9]:
                        target_mask[s_id] = 1
                elif event == "ESCAPADE_SH":
                    # DR Base (7)
                    if int(sp.pieces[7]) > 0:
                        target_mask[s_id] = 1
                elif event == "LOECHES_UN":
                    stage = pending.get("stage", "PLACE")
                    if stage == "PLACE":
                        target_mask[s_id] = 1
                    else:
                        if s_id == pending.get("place_id"):
                            target_mask[s_id] = 1
                elif event == "LOECHES_UN_MARCH":
                    dest = pending.get("dest")
                    if dest is None:
                        continue
                    if s_id == dest:
                        continue
                    if "Morgan_Unshaded" in self.capabilities:
                        dist = self._shortest_space_distances(dest)
                        if dist.get(s_id, 999) <= 2 and int(sp.pieces[5] + sp.pieces[6]) > 0:
                            target_mask[s_id] = 1
                    else:
                        if s_id in self.board.spaces[dest].adj_ids and int(sp.pieces[5] + sp.pieces[6]) > 0:
                            target_mask[s_id] = 1
                elif event == "LOECHES_SH":
                    # DR Guerrilla
                    if int(sp.pieces[5] + sp.pieces[6]) > 0:
                        target_mask[s_id] = 1
                elif event == "ECHEVERRIA_UN":
                    target_mask[s_id] = 1
                elif event == "CHOMON_SH":
                    # DR piece
                    if int(sp.pieces[5] + sp.pieces[6] + sp.pieces[7]) > 0:
                        target_mask[s_id] = 1
                elif event == "ESCOPETEROS_UN":
                    if sp.type == 3: # Mountain
                        target_mask[s_id] = 1
                elif event == "ESCOPETEROS_SH":
                    if sp.type == 3: # Mountain
                        target_mask[s_id] = 1
                elif event == "RESISTENCIA_UN":
                    if sp.type == 0 and int(sp.pieces[5] + sp.pieces[6] + sp.pieces[7]) > 0:
                        target_mask[s_id] = 1
                elif event == "RESISTENCIA_SH":
                    if sp.type == 0 and int(sp.pieces[2] + sp.pieces[3] + sp.pieces[4]) > 0:
                        target_mask[s_id] = 1
                elif event == "ECHEVERRIA_SH":
                    if int(sp.pieces[5] + sp.pieces[6] + sp.pieces[7]) > 0:
                        dist = self._shortest_space_distances(3)
                        min_dist = None
                        for sp2 in self.board.spaces:
                            if int(sp2.pieces[5] + sp2.pieces[6] + sp2.pieces[7]) <= 0:
                                continue
                            d = dist.get(sp2.id, 999)
                            if min_dist is None or d < min_dist:
                                min_dist = d
                        if min_dist is not None and dist.get(s_id, 999) == min_dist:
                            target_mask[s_id] = 1
                elif event == "DEFECTIONS_UN":
                    stage = pending.get("stage", "SPACE")
                    if stage == "SPACE":
                        p_idx = self.current_player_num
                        # Per 2018 rulebook: "pieces" includes bases
                        has_ours = self._any_piece_present_for_faction(sp, p_idx)
                        has_enemy = any(
                            self._any_piece_present_for_faction(sp, f)
                            for f in range(4) if f != p_idx
                        )
                        if has_ours and has_enemy:
                            target_mask[s_id] = 1
                elif event == "MENOYO_UN":
                    # Within 1 space of Las Villas (5)
                    if s_id == 5 or s_id in self.board.spaces[5].adj_ids:
                        # Must have non-DR non-Casino piece
                        # DR is 5,6,7. Casino is 10.
                        others = sp.pieces[0]+sp.pieces[1]+sp.pieces[2]+sp.pieces[3]+sp.pieces[4]+sp.pieces[8]+sp.pieces[9] + sp.govt_bases
                        if others > 0:
                            target_mask[s_id] = 1
                elif event == "MENOYO_SH":
                    # DR Guerrilla
                    if int(sp.pieces[5] + sp.pieces[6]) > 0:
                        target_mask[s_id] = 1
                elif event == "MEYER_LANSKY_UN":
                    stage = pending.get("stage", "SPACE")
                    if stage == "SPACE":
                        has_cash = self._space_total_cash(sp) > 0
                        if has_cash and self._space_has_valid_cash_transfer_between_holders(sp):
                            target_mask[s_id] = 1
                elif event == "MEYER_LANSKY_SH":
                    stage = pending.get("stage", "SRC")
                    if stage == "SRC":
                        if int(sp.pieces[10]) > 0:
                            has_dest = any(
                                self._can_place_casino(self.board.spaces[d_id])
                                for d_id in range(self.num_spaces)
                                if d_id != s_id
                            )
                            if has_dest:
                                target_mask[s_id] = 1
                    else:
                        src_id = pending.get("src")
                        if src_id is None or s_id == src_id:
                            continue
                        if self._can_place_casino(sp):
                            target_mask[s_id] = 1
                elif event == "GUERRILLA_LIFE_SH":
                    # Place a DR Guerrilla in a City.
                    if sp.type == 0 and int(self.players[2].available_forces[0]) > 0:
                        target_mask[s_id] = 1
                elif event == "MANIFESTO_UN":
                    # Each faction may place 2 non-Casino pieces in a space where they already have a piece.
                    f_idx = int(pending.get("f_idx", 0))
                    # "Already have a piece" includes bases/casinos.
                    if f_idx == 0:
                        has_ours = int(sp.pieces[0] + sp.pieces[1] + sp.govt_bases) > 0
                        has_available = int(self.players[0].available_forces[0] + self.players[0].available_forces[1] + self.players[0].available_bases) > 0
                    elif f_idx == 1:
                        has_ours = int(sp.pieces[2] + sp.pieces[3] + sp.pieces[4]) > 0
                        has_available = int(self.players[1].available_forces[0] + self.players[1].available_bases) > 0
                    elif f_idx == 2:
                        has_ours = int(sp.pieces[5] + sp.pieces[6] + sp.pieces[7]) > 0
                        has_available = int(self.players[2].available_forces[0] + self.players[2].available_bases) > 0
                    else:
                        has_ours = int(sp.pieces[8] + sp.pieces[9] + sp.pieces[10]) > 0
                        # Syndicate: non-Casino pieces excludes Casinos.
                        has_available = int(self.players[3].available_forces[0]) > 0
                    if has_ours and has_available:
                        target_mask[s_id] = 1
                elif event == "THE_TWELVE_SH":
                    max_g = int(pending.get("max", 0))
                    if max_g > 0:
                        g = int(sp.pieces[2] + sp.pieces[3] + sp.pieces[5] + sp.pieces[6] + sp.pieces[8] + sp.pieces[9])
                        if g == max_g:
                            target_mask[s_id] = 1
                elif event == "CARLOS_PRIO_SH":
                    # Space without Govt Control
                    if int(self.players[2].available_bases) > 0 and sp.controlled_by != 1:
                        target_mask[s_id] = 1
                elif event == "MORGAN_SH":
                    # Space with DR Guerrilla
                    if int(sp.pieces[5] + sp.pieces[6]) > 0:
                        target_mask[s_id] = 1
                elif event == "MIAMI_UN":
                    # Any guerrilla
                    if int(sp.pieces[2] + sp.pieces[3] + sp.pieces[5] + sp.pieces[6] + sp.pieces[8] + sp.pieces[9]) > 0:
                        target_mask[s_id] = 1

                # --- Ops targeting (source selection) ---
                elif op_kind == "TRANSPORT_SRC":
                    dest = pending_op.get("dest")
                    if dest is None or s_id == dest:
                        continue
                    if sp.pieces[0] > 0:
                        target_mask[s_id] = 1
                elif op_kind == "ASSAULT_REINFORCE_SRC":
                    mask[self._main_action_base + MAIN_PASS] = 1
                    dest = pending_op.get("dest")
                    if dest is None or s_id == dest:
                        continue
                    if int(sp.pieces[0]) > 0:
                        target_mask[s_id] = 1
                elif op_kind == "MARCH_SRC":
                    mask[self._main_action_base + MAIN_PASS] = 1
                    dest = pending_op.get("dest")
                    u = pending_op.get("u")
                    a = pending_op.get("a")
                    if dest is None or u is None or a is None:
                        continue
                    if s_id in self._march_source_ids(pending_op):
                        target_mask[s_id] = 1
                elif op_kind == "SWEEP_SRC":
                    mask[self._main_action_base + MAIN_PASS] = 1
                    if s_id in self._sweep_sources(pending_op):
                        target_mask[s_id] = 1
                elif op_kind == "GARRISON_SRC":
                    mask[self._main_action_base + MAIN_PASS] = 1
                    if s_id in self._garrison_sources(pending_op):
                        target_mask[s_id] = 1

            mask[self._target_space_action_base:self._target_space_action_base + self._target_space_action_count] = target_mask
            return mask

        # Phase 6: choose a target faction (event-driven)
        if self.phase == PHASE_CHOOSE_TARGET_FACTION:
            if self._pending_launder is not None and self._pending_launder.get("stage") == "PROVIDER":
                mask[self._main_action_base + MAIN_PASS] = 1
                target_mask = np.zeros(self._target_faction_action_count)
                for f in self._launder_provider_factions():
                    target_mask[f] = 1
                mask[self._target_faction_action_base:self._target_faction_action_base + self._target_faction_action_count] = target_mask
                return mask
            pending = self._pending_event_faction
            if pending is None:
                return mask

            event = pending.get("event")
            allowed = pending.get("allowed") or []

            for f in allowed:
                mask[self._target_faction_action_base + int(f)] = 1
            return mask

        # Phase 7: choose an event option (event-driven)
        if self.phase == PHASE_CHOOSE_EVENT_OPTION:
            pending = self._pending_event_option
            if pending is None:
                return mask
            allowed = pending.get("allowed") or []
            for opt in allowed:
                mask[self._event_option_action_base + int(opt)] = 1
            return mask

        # Phase 8: choose a target piece (cash-transfer resolution)
        if self.phase == PHASE_CHOOSE_TARGET_PIECE:
            if self._pending_cash_transfers:
                pending = self._pending_cash_transfers[0]
                sp = self.board.spaces[int(pending.get("space_id"))]
                target_mask = np.zeros(self._target_piece_action_count)
                for idx in range(len(sp.pieces)):
                    if int(sp.pieces[idx]) > 0:
                        target_mask[idx] = 1
                target_mask[self._target_piece_action_count - 1] = 1  # remove cash
                mask[self._target_piece_action_base:self._target_piece_action_base + self._target_piece_action_count] = target_mask
                return mask

            # Meyer Lansky (Un): agent-driven cash holder-to-holder transfers within a space.
            pending_target = self._pending_event_target
            if pending_target is not None and pending_target.get("event") == "MEYER_LANSKY_UN":
                stage = pending_target.get("stage")
                space_id = pending_target.get("space")
                if space_id is None:
                    return mask
                sp = self.board.spaces[int(space_id)]

                target_mask = np.zeros(self._target_piece_action_count)
                if stage == "SRC_HOLDER":
                    for idx in range(len(sp.cash_holders)):
                        if int(sp.cash_holders[idx]) > 0:
                            target_mask[idx] = 1
                    target_mask[self._target_piece_action_count - 1] = 1  # stop
                elif stage == "DEST_HOLDER":
                    src_holder = pending_target.get("src_holder")
                    if src_holder is None:
                        return mask
                    has_any_dest = False
                    for idx in range(len(sp.pieces)):
                        if int(sp.pieces[idx]) > 0 and int(idx) != int(src_holder):
                            target_mask[idx] = 1
                            has_any_dest = True
                    # Always allow stop as fallback (handles edge case of no valid destinations)
                    target_mask[self._target_piece_action_count - 1] = 1

                mask[self._target_piece_action_base:self._target_piece_action_base + self._target_piece_action_count] = target_mask
                return mask
            return mask

        # Phase 2: choose Ops action (existing op×space encoding)
        if self.phase == PHASE_CHOOSE_OP_ACTION:
            ops_mask = np.zeros(self._ops_action_count)

            if player.name == "GOVT":
                can_afford = player.resources >= self.get_govt_cost()
                any_troops = any(int(sp.pieces[0]) > 0 for sp in self.board.spaces)
                for s_id in range(self.num_spaces):
                    s = self.board.spaces[s_id]; gp = s.pieces[0]+s.pieces[1]
                    if can_afford:
                        is_city = (s.type == 0)
                        if is_city or s.govt_bases > 0:
                            if any(player.available_forces): ops_mask[OP_TRAIN_FORCE*13+s_id]=1
                            if gp>=2 and player.available_bases>0 and s.govt_bases<(2 if is_city else 1): ops_mask[OP_TRAIN_BASE*13+s_id]=1
                        if any(self.board.spaces[i].pieces[1]>0 for i in s.adj_ids): ops_mask[OP_GARRISON*13+s_id]=1

                        has_adj_troops = any(self.board.spaces[i].pieces[0]>0 for i in s.adj_ids)
                        if gp>0 or has_adj_troops: ops_mask[OP_SWEEP*13+s_id]=1

                        # Assault
                        enemies = sum(s.pieces[2:11])
                        can_assault = (gp > 0 and enemies > 0)
                        if can_assault:
                            ops_mask[OP_ASSAULT*13+s_id]=1

                        # Transport
                        if any_troops:
                            ops_mask[OP_TRANSPORT*13+s_id]=1

                        # Air Strike is treated as a Special Activity (handled in PHASE_CHOOSE_SPECIAL_ACTIVITY)

            elif player.name in ["M26", "DR", "SYNDICATE"]:
                can_afford = self._launder_free or (player.resources >= 1)
                if player.name == "M26":
                    u,a,b=2,3,4; base=7
                elif player.name == "DR":
                    u,a,b=5,6,7; base=11
                else:
                    u,a,b=8,9,10; base=18

                for s_id in range(self.num_spaces):
                    s = self.board.spaces[s_id]; cnt = s.pieces[u]+s.pieces[a]
                    has_govt = (s.pieces[0]+s.pieces[1]+s.govt_bases)>0
                    if can_afford:
                        ops_mask[base*13+s_id]=1
                        if player.name == "DR" and "Morgan_Unshaded" in self.capabilities:
                            if self._has_guerrillas_within_range(s_id, u, a, 2):
                                ops_mask[(base+1)*13+s_id]=1
                        else:
                            if any((self.board.spaces[i].pieces[u]+self.board.spaces[i].pieces[a])>0 for i in s.adj_ids):
                                ops_mask[(base+1)*13+s_id]=1
                        if cnt>0 and has_govt: ops_mask[(base+2)*13+s_id]=1
                        if s.pieces[u]>0:
                            if self._pact_blocks_opposition(self.current_player_num):
                                pass
                            else:
                                ops_mask[(base+3)*13+s_id]=1

            # Event/Pass are not part of the Ops-phase menu.
            # Note: Pass is handled in PHASE_CHOOSE_MAIN.
            mask[self._ops_action_base:self._ops_action_base + self._ops_action_count] = ops_mask
            return mask

        # Phase 4: choose Special Activity or skip (uses existing op×space encoding)
        if self.phase == PHASE_CHOOSE_SPECIAL_ACTIVITY:
            # Reuse MAIN_PASS as "skip special activity" to avoid expanding the action space.
            mask[self._main_action_base + MAIN_PASS] = 1

            sa_mask = np.zeros(self._ops_action_count)
            if player.name == "GOVT":
                can_afford = True if self._sa_free else (player.resources >= self.get_govt_cost())
                if can_afford:
                    for s_id in range(self.num_spaces):
                        s = self.board.spaces[s_id]
                        has_active = (s.pieces[3]+s.pieces[6]+s.pieces[9])>0
                        ignore_embargo = "Guantanamo_Shaded" in self.capabilities
                        if (self.us_alliance != US_ALLIANCE_EMBARGOED or ignore_embargo) and s.type in [1, 3] and has_active:
                            sa_mask[OP_AIR_STRIKE*13+s_id]=1

                # Masferrer (shaded): Sweep may free Assault 1 space as its Special Activity.
                if self._sa_restrict_op is not None and self._sa_restrict_space is not None:
                    sa_mask[:] = 0
                    sa_mask[self._sa_restrict_op * self.num_spaces + self._sa_restrict_space] = 1
            elif player.name == "M26":
                can_afford = player.resources >= 1
                if can_afford:
                    for s_id in range(self.num_spaces):
                        s = self.board.spaces[s_id]
                        u,a = 2,3
                        cnt = s.pieces[u]+s.pieces[a]
                        has_govt = (s.pieces[0]+s.pieces[1]+s.govt_bases)>0
                        # Ambush: Any space with M26 guerrillas and any enemy
                        enemies = sum(s.pieces[5:11]) + (s.pieces[0] + s.pieces[1] + s.govt_bases)
                        if cnt>0 and enemies>0:
                            sa_mask[OP_AMBUSH_M26*13+s_id]=1
                        # Kidnap: City/EC/Sierra Maestra (with capability) + M26 guerrillas > Police + open casino (or City/EC)
                        allow_loc = (s.type in [0,4])  # City or EC
                        if s.name == "Sierra Maestra" and "Guantanamo_Unshaded" in self.capabilities:
                            allow_loc = True
                        m26_count = int(s.pieces[u] + s.pieces[a])
                        police_count = int(s.pieces[1])
                        has_open_casino = int(s.pieces[10]) > 0
                        # Kidnap requires: (City/EC OR open casino OR Sierra w/ Guantanamo cap) AND M26 > Police
                        guantanamo_city = (s.name == "Sierra Maestra" and "Guantanamo_Unshaded" in self.capabilities)
                        if allow_loc and s.pieces[u] > 0 and m26_count > police_count and not self._pact_blocks_opposition(self.current_player_num):
                            if s.type in [0, 4] or has_open_casino or guantanamo_city:
                                sa_mask[OP_KIDNAP_M26*13+s_id] = 1
            elif player.name == "DR":
                can_afford = player.resources >= 1
                if can_afford:
                    for s_id in range(self.num_spaces):
                        s = self.board.spaces[s_id]
                        u,a = 5,6
                        cnt = s.pieces[u]+s.pieces[a]
                        # Ambush: Any space with DR guerrillas and any enemy
                        enemies = sum(s.pieces[2:5]) + sum(s.pieces[8:11]) + (s.pieces[0] + s.pieces[1] + s.govt_bases)
                        if cnt>0 and enemies>0:
                            if (OP_AMBUSH_DR * 13 + s_id) < len(sa_mask):
                                sa_mask[OP_AMBUSH_DR*13+s_id]=1

                        # Assassinate: City or EC where DR > Police, targets any enemy.
                        # Rule 4.4.3: "DR Guerrillas outnumber Police."
                        dr_count = int(s.pieces[u] + s.pieces[a])
                        police_count = int(s.pieces[1])
                        if s.type in [0, 4] and cnt > 0 and enemies > 0 and dr_count > police_count and not self._pact_blocks_opposition(self.current_player_num):
                            if (OP_ASSASSINATE_DR * 13 + s_id) < len(sa_mask):
                                sa_mask[OP_ASSASSINATE_DR*13+s_id] = 1

                        # Ambush: Rule 4.4.2
                        if cnt > 0 and enemies > 0:
                             if (OP_AMBUSH_DR * 13 + s_id) < len(sa_mask):
                                  sa_mask[OP_AMBUSH_DR * 13 + s_id] = 1
            elif player.name == "SYNDICATE":
                can_afford = player.resources >= 1
                if can_afford:
                    for s_id in range(self.num_spaces):
                        s = self.board.spaces[s_id]
                        u,a = 8,9
                        cnt = s.pieces[u]+s.pieces[a]
                        has_govt = (s.pieces[0] + s.pieces[1] + s.govt_bases) > 0
                        # Bribe: Any space with Syndicate guerrillas (no terrain restriction)
                        if cnt>0:
                            sa_mask[OP_BRIBE_SYN*13+s_id]=1
                        # Construct: Any space (handled as Operation, not SA)
                        if cnt>0 and player.available_bases>0:
                            sa_mask[OP_CONSTRUCT_SYN*13+s_id]=1
                        # Hitmen (shaded): Syndicate may Assassinate as if DR, but regardless of Police.
                        if "Hitmen_Shaded" in self.capabilities:
                            if cnt > 0 and has_govt:
                                sa_mask[OP_ASSASSINATE_DR*13+s_id] = 1

            mask[self._ops_action_base:self._ops_action_base + self._ops_action_count] = sa_mask
            return mask

        # Phase 3: choose Limited Ops action (event-driven overrides)
        if self.phase == PHASE_CHOOSE_LIMITED_OP_ACTION and self._pending_mafia_offensive is not None:
            ops_mask = np.zeros(self._limited_ops_action_count)
            faction = int(self._pending_mafia_offensive.get("faction"))
            can_afford = True  # Free LimOp
            if faction == 1:
                u, a, b = 2, 3, 4
                base = 7
            else:
                u, a, b = 5, 6, 7
                base = 11

            for s_id in range(self.num_spaces):
                s = self.board.spaces[s_id]
                cnt = int(s.pieces[u] + s.pieces[a])
                syn_cnt = int(s.pieces[8] + s.pieces[9])
                has_govt = (s.pieces[0] + s.pieces[1] + s.govt_bases) > 0
                if can_afford:
                    ops_mask[base * 13 + s_id] = 1  # Rally
                    has_adj = any(
                        (self.board.spaces[i].pieces[u] + self.board.spaces[i].pieces[a] + self.board.spaces[i].pieces[8] + self.board.spaces[i].pieces[9]) > 0
                        for i in s.adj_ids
                    )
                    if has_adj:
                        ops_mask[(base + 1) * 13 + s_id] = 1  # March
                    if (cnt + min(1, syn_cnt)) > 0 and has_govt:
                        ops_mask[(base + 2) * 13 + s_id] = 1  # Attack
                    if s.pieces[u] > 0 or s.pieces[8] > 0:
                        if self._pact_blocks_opposition(faction):
                            pass
                        else:
                            ops_mask[(base + 3) * 13 + s_id] = 1  # Terror

            mask[self._limited_ops_action_base:self._limited_ops_action_base + self._limited_ops_action_count] = ops_mask
            return mask

        if self.phase == PHASE_CHOOSE_LIMITED_OP_ACTION:
            ops_mask = np.zeros(self._limited_ops_action_count)

            if player.name == "GOVT":
                can_afford = self._launder_free or (player.resources >= self.get_govt_cost())
                any_troops = any(int(sp.pieces[0]) > 0 for sp in self.board.spaces)
                for s_id in range(self.num_spaces):
                    s = self.board.spaces[s_id]; gp = s.pieces[0]+s.pieces[1]
                    if can_afford:
                        is_city = (s.type == 0)
                        if is_city or s.govt_bases > 0:
                            if any(player.available_forces): ops_mask[OP_TRAIN_FORCE*13+s_id]=1
                            if gp>=2 and player.available_bases>0 and s.govt_bases<(2 if is_city else 1): ops_mask[OP_TRAIN_BASE*13+s_id]=1
                        if any(self.board.spaces[i].pieces[1]>0 for i in s.adj_ids): ops_mask[OP_GARRISON*13+s_id]=1

                        has_adj_troops = any(self.board.spaces[i].pieces[0]>0 for i in s.adj_ids)
                        if gp>0 or has_adj_troops: ops_mask[OP_SWEEP*13+s_id]=1

                        enemies = sum(s.pieces[2:11])
                        can_assault = (gp > 0 and enemies > 0)
                        if can_assault:
                            ops_mask[OP_ASSAULT*13+s_id]=1

                        if gp > 0:
                            pass

                        if any_troops:
                            ops_mask[OP_TRANSPORT*13+s_id]=1

                        # No Air Strike in Limited Ops

            elif player.name in ["M26", "DR", "SYNDICATE"]:
                can_afford = self._launder_free or (player.resources >= 1)
                if player.name == "M26":
                    u,a,b=2,3,4; base=7
                elif player.name == "DR":
                    u,a,b=5,6,7; base=11
                else:
                    u,a,b=8,9,10; base=18

                for s_id in range(self.num_spaces):
                    s = self.board.spaces[s_id]; cnt = s.pieces[u]+s.pieces[a]
                    has_govt = (s.pieces[0]+s.pieces[1]+s.govt_bases)>0
                    if can_afford:
                        ops_mask[base*13+s_id]=1
                        if player.name == "DR" and "Morgan_Unshaded" in self.capabilities:
                            if self._has_guerrillas_within_range(s_id, u, a, 2):
                                ops_mask[(base+1)*13+s_id]=1
                        elif any((self.board.spaces[i].pieces[u]+self.board.spaces[i].pieces[a])>0 for i in s.adj_ids):
                            ops_mask[(base+1)*13+s_id]=1
                        if cnt>0 and has_govt: ops_mask[(base+2)*13+s_id]=1
                        if s.pieces[u]>0:
                            if self._pact_blocks_opposition(self.current_player_num):
                                pass
                            else:
                                ops_mask[(base+3)*13+s_id]=1

                        # Construct is a Syndicate Operation and is allowed as a paid Limited Operation,
                        # but is never free (2.3.6 / 3.3.5). So forbid it when Launder grants a free LimOp.
                        if player.name == "SYNDICATE" and not self._launder_free:
                            if cnt > 0 and player.available_bases > 0:
                                ops_mask[OP_CONSTRUCT_SYN * 13 + s_id] = 1

                        # No special activities in Limited Ops

            mask[self._limited_ops_action_base:self._limited_ops_action_base + self._limited_ops_action_count] = ops_mask
            return mask

        return mask


    def action_masks(self):
        """Return boolean mask for MaskablePPO. True = action is valid.

        Per COIN rules, ineligible factions are skipped entirely (no action,
        no resource gain).  If we detect an all-zeros mask caused by an
        ineligible player sitting at PHASE_CHOOSE_MAIN, we auto-advance the
        turn pointer until we reach an eligible player or a new card, then
        return that player's mask.

        Additionally, events can "fizzle" — transitioning to a target
        selection phase where no valid targets exist.  In that case we clean
        up the pending event state and advance the turn.
        """
        la = np.array(self.legal_actions, dtype=bool)
        # Auto-skip ineligible players (guards against infinite loops)
        safety = 0
        while not la.any() and safety < 20:
            if self.deck_empty:
                # Game Over triggered during auto-advance. Return dummy mask to allow step() call.
                la[0] = 1
                break
            safety += 1
            player = self.players[self.current_player_num]
            if self.phase == 0 and not player.eligible:
                print(f"  (auto-skip ineligible {player.name})")
                self.card_action_slot += 1
                self.update_turn_pointer()
                la = np.array(self.legal_actions, dtype=bool)
            elif self.phase in [5, 6, 7, 8, 2, 3, 4]:
                # Event / multi-step action fizzled — no valid targets.
                pending = self._pending_event_target
                pending_f = getattr(self, '_pending_event_faction', None)
                pending_o = getattr(self, '_pending_event_option', None)
                pending_op = self._pending_op_target
                fizzle_label = (
                    (pending.get("event") if pending else None) or
                    (pending_f.get("event") if pending_f else None) or
                    (pending_o.get("event") if pending_o else None) or
                    (pending_op.get("op") if pending_op else None) or
                    f"phase-{self.phase}"
                )
                print(f"  (event fizzle: {fizzle_label} — no valid targets for {player.name})")
                # Clean up all pending state
                self._pending_event_target = None
                self._pending_event_faction = None
                self._pending_event_option = None
                self._pending_op_target = None
                self._pending_main = None
                # Mark player ineligible and advance
                player.eligible = False
                if not getattr(self, "keep_eligible_this_action", False):
                    self.ineligible_next_card.add(self.current_player_num)
                self.card_action_slot += 1
                self.phase = 0
                self._pending_sa = None
                self._sa_free = False
                self._sa_from_limited_ops = False
                self._sa_restrict_op = None
                self._sa_restrict_space = None
                self.update_turn_pointer()
                la = np.array(self.legal_actions, dtype=bool)
            else:
                print(f"WARNING: All-zeros mask! phase={self.phase}, player={player.name}, "
                      f"eligible={player.eligible}")
                break

        if not la.any():
            la[0] = True

        return la
