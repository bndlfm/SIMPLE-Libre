import gymnasium as gym


import numpy as np
import random
from collections import deque
from .classes import *
from .constants import *
from .mixins.step import StepMixin
from .mixins.legal_actions import LegalActionsMixin
from .mixins.propaganda import PropagandaMixin
from .mixins.govt_ops import GovtOpsMixin
from .mixins.insurgent_ops import InsurgentOpsMixin

from .data import EVENT_DECK_DATA
from .events import resolve_event, _free_ambush_against_govt, _free_ambush_against_govt_bases_first, _shift_alignment



class CubaLibreEnv(StepMixin, LegalActionsMixin, PropagandaMixin, GovtOpsMixin, InsurgentOpsMixin, gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, verbose=False, manual=False, same_player_control=True):
        super(CubaLibreEnv, self).__init__()
        self.name = 'cubalibre'
        self.n_players = 4 
        self.factions_list = FACTIONS
        self.manual = manual
        self.same_player_control = bool(same_player_control)
        self.verbose = verbose
        self.num_spaces = 13
        self.space_feature_size = 13 
        self.num_ops = 26

        # Action space is now partitioned into 3 regions:
        # - Main-choice actions
        # - Event-side actions
        # - Ops actions (existing op×space encoding)
        self._main_action_base = 0
        self._main_action_count = 3
        self._event_side_base = self._main_action_base + self._main_action_count
        self._event_side_count = 2
        self._ops_action_base = self._event_side_base + self._event_side_count
        self._ops_action_count = self.num_ops * self.num_spaces
        self._limited_main_action_id = self._ops_action_base + self._ops_action_count
        self._limited_ops_action_base = self._limited_main_action_id + 1
        self._limited_ops_action_count = self.num_ops * self.num_spaces
        self._target_space_action_base = self._limited_ops_action_base + self._limited_ops_action_count
        self._target_space_action_count = self.num_spaces
        self._target_faction_action_base = self._target_space_action_base + self._target_space_action_count
        self._target_faction_action_count = self.n_players
        self._event_option_action_base = self._target_faction_action_base + self._target_faction_action_count
        self._event_option_action_count = 3
        self._target_piece_action_base = self._event_option_action_base + self._event_option_action_count
        self._target_piece_action_count = 13  # 0-10 piece indices, 11 = govt base, 12 = remove cash/stop
        self.action_space = gym.spaces.Discrete(self._target_piece_action_base + self._target_piece_action_count)
        # Observation header fields (see observation() property)
        self._obs_header_size = 15  # Expanded to include next_card.id
        self.obs_size = self._obs_header_size + (self.num_spaces * self.space_feature_size)
        self.observation_space = gym.spaces.Box(low=-1, high=50, shape=(self.obs_size,), dtype=np.float32)
        # 2018 campaign track: US Alliance (Firm/Reluctant/Embargoed)
        self.set_us_alliance(US_ALLIANCE_FIRM)
        # 2018 campaign track: Aid (0-49)
        self.set_aid(0)
        # 2018 campaign edge tracks (stored explicitly, refreshed as state changes)
        self.total_support_track = 0
        self.opposition_plus_bases_track = 0
        self.dr_pop_plus_bases_track = 0
        self.open_casinos_track = 0
        self.done = False
        self.current_card = None
        self.next_card = None  # Peek at next card (board game mechanic)
        self.deck_empty = False
        self.propaganda_cards_played = 0
        self.factions_acted_this_card = 0
        self.card_action_slot = 0
        self._card_order_index = 0
        self.card_first_actor = None
        self.card_second_actor = None
        self.card_first_action = None
        self.final_victory_margins_result = None
        self.final_victory_ranking_result = None
        self.capabilities = set()
        self.phase = PHASE_CHOOSE_MAIN
        self._pending_main = None
        self.keep_eligible_this_action = False
        self._pending_cash_transfers = deque()
        self._cash_transfer_waiting = False
        self._cash_transfer_active = False
        self._cash_transfer_return_player = None
        self._cash_transfer_return_phase = None
        self._cash_transfer_return_advance = False
        self.ineligible_through_next_card = set()
        self.ineligible_next_card = set()
        self._pending_sa = None
        self._sa_free = False
        self._sa_from_limited_ops = False
        self._launder_used_this_card = False
        self._pending_launder = None
        self._launder_actor = None
        self._launder_free = False
        self._last_op_paid_cost = 0
        self._last_op = None
        self._last_op_space = None
        self._sa_restrict_op = None
        self._sa_restrict_space = None
        self._pending_event_target = None
        self._pending_op_target = None
        self._pending_event_faction = None
        self._pending_event_option = None
        self._propaganda_in_progress = False
        self._propaganda_final_round = False
        self._pending_propaganda = None
        self._propaganda_in_progress = False
        self._pact_removed_bases_this_action = None
        self._propaganda_final_round = False
        self._pending_propaganda = None
        self._pending_mafia_offensive = None

    def get_govt_cost(self):
        if self.us_alliance == US_ALLIANCE_FIRM:
            return 2
        if self.us_alliance == US_ALLIANCE_RELUCTANT:
            return 3
        return 4
    def _roll_die(self): return random.randint(1, 6)

    def _clamp_aid(self, value):
        return max(0, min(49, int(value)))

    def _clamp_us_alliance(self, value):
        return max(US_ALLIANCE_FIRM, min(US_ALLIANCE_EMBARGOED, int(value)))

    def set_aid(self, value):
        self.aid = self._clamp_aid(value)

    def shift_aid(self, delta):
        self.aid = self._clamp_aid(int(self.aid) + int(delta))

    def set_us_alliance(self, value):
        self.us_alliance = self._clamp_us_alliance(value)

    def shift_us_alliance(self, delta):
        self.us_alliance = self._clamp_us_alliance(int(self.us_alliance) + int(delta))

    def score_game(self):
        scores = [0.0] * 4
        govt_pts = 0; m26_pts = 0; dr_pts = 0; syn_casinos = 0
        m26_bases = 0; dr_bases = 0
        for s in self.board.spaces:
            if s.alignment == 1: govt_pts += s.population
            if s.controlled_by == 1: govt_pts += s.population
            if s.alignment == 2: m26_pts += s.population
            m26_bases += s.pieces[4]
            if s.controlled_by == 3: dr_pts += s.population
            dr_bases += s.pieces[7]
            syn_casinos += s.pieces[10]
        scores[0] = govt_pts
        scores[1] = m26_pts + m26_bases
        scores[2] = dr_pts + dr_bases
        scores[3] = syn_casinos + self.players[3].resources
        return scores

    def victory_margins(self):
        # 7.3 After Final Propaganda: victory margins relative to each faction's condition.
        self._refresh_campaign_tracks()
        govt_margin = int(self.total_support_track) - 18
        m26_margin = int(self.opposition_plus_bases_track) - 15
        dr_margin = int(self.dr_pop_plus_bases_track) - 9
        syn_margin = min(int(self.open_casinos_track) - 7, int(self.players[3].resources) - 30)
        return [govt_margin, m26_margin, dr_margin, syn_margin]

    def final_victory_ranking(self):
        # 7.1/7.3: higher margin ranks higher; ties go to Syndicate, then DR, then 26July, then Govt.
        margins = self.victory_margins()
        tie_rank = {3: 0, 2: 1, 1: 2, 0: 3}
        return sorted(range(4), key=lambda f: (-margins[f], tie_rank[f]))

    # --- DERIVED VICTORY MARKERS (2018 edge track) ---
    def _iter_pop_spaces(self):
        # Population spaces are Cities (type 0) and Provinces (types 1-3).
        for sp in self.board.spaces:
            if sp.type in [0, 1, 2, 3]:
                yield sp

    def total_support_value(self):
        # Total Support equals:
        # (2 x Pop in Active Support) + (1 x Pop in Passive Support)
        total = 0
        for sp in self._iter_pop_spaces():
            if sp.alignment == 1:
                total += sp.population * (2 if sp.support_active else 1)
        return int(total)

    def total_opposition_value(self):
        # Total Opposition equals:
        # (2 x Pop in Active Opposition) + (1 x Pop in Passive Opposition)
        total = 0
        for sp in self._iter_pop_spaces():
            if sp.alignment == 2:
                total += sp.population * (2 if sp.support_active else 1)
        return int(total)

    def opposition_plus_bases_value(self):
        # Opposition + Bases equals:
        # Total Opposition + the number of 26July Bases on the map
        total_opp = self.total_opposition_value()
        m26_bases = sum(int(sp.pieces[4]) for sp in self.board.spaces)
        return int(total_opp + m26_bases)

    def dr_pop_plus_bases_value(self):
        # DR Pop + Bases equals:
        # Population of all spaces Controlled by Directorio + the number of Directorio Bases on the map
        dr_bases = sum(int(sp.pieces[7]) for sp in self.board.spaces)
        dr_pop = 0
        for sp in self._iter_pop_spaces():
            # Some code paths directly mutate pieces without calling update_control.
            sp.update_control()
            if sp.controlled_by == 3:
                dr_pop += sp.population
        return int(dr_pop + dr_bases)

    def open_casinos_value(self):
        # Open Casinos: count of Syndicate Casinos on the map.
        # Note: the current model does not distinguish open/closed explicitly; pieces[10] represent open casinos.
        return int(sum(int(sp.pieces[10]) for sp in self.board.spaces))

    def _refresh_campaign_tracks(self):
        self.total_support_track = self.total_support_value()
        self.opposition_plus_bases_track = self.opposition_plus_bases_value()
        self.dr_pop_plus_bases_track = self.dr_pop_plus_bases_value()
        self.open_casinos_track = self.open_casinos_value()

    def _space_has_faction_pieces(self, sp, faction_idx):
        if faction_idx == 0:
            return int(sp.pieces[0] + sp.pieces[1]) > 0
        if faction_idx == 1:
            return int(sp.pieces[2] + sp.pieces[3]) > 0
        if faction_idx == 2:
            return int(sp.pieces[5] + sp.pieces[6]) > 0
        return int(sp.pieces[8] + sp.pieces[9]) > 0

    def _cash_piece_indices_for_faction(self, faction_idx):
        if faction_idx == 0:
            return [0, 1]  # Troops, Police
        if faction_idx == 1:
            return [2, 3]  # M26 U/A Guerrillas
        if faction_idx == 2:
            return [5, 6]  # DR U/A Guerrillas
        return [8, 9]      # Syn U/A Guerrillas

    def _faction_for_piece_index(self, idx):
        if idx < 2:
            return 0
        if idx < 5:
            return 1
        if idx < 8:
            return 2
        return 3

    def _queue_cash_transfers_for_space(self, sp):
        queued = False
        for idx in range(len(sp.cash_holders)):
            if int(sp.pieces[idx]) == 0 and int(sp.cash_holders[idx]) > 0:
                cash_to_move = int(sp.cash_holders[idx])
                faction_idx = self._faction_for_piece_index(idx)
                self._queue_cash_transfer(sp.id, faction_idx, idx, cash_to_move)
                queued = True
        if queued:
            self._refresh_space_cash_counts(sp)
            if self.phase == PHASE_CHOOSE_MAIN and not self._cash_transfer_active:
                pending = self._pending_cash_transfers[0]
                self.current_player_num = int(pending.get("owner"))
                self.phase = PHASE_CHOOSE_TARGET_PIECE
                self._cash_transfer_active = True
        return queued

    def _space_cash_by_faction(self, sp, faction_idx):
        return int(sum(int(sp.cash_holders[idx]) for idx in self._cash_piece_indices_for_faction(faction_idx)))

    def _space_total_cash(self, sp):
        return int(np.sum(sp.cash_holders))

    def _refresh_space_cash_counts(self, sp):
        if hasattr(sp, "refresh_cash_counts"):
            sp.refresh_cash_counts()
            return
        sp.cash[:] = 0
        for f in range(4):
            sp.cash[f] = self._space_cash_by_faction(sp, f)

    def _queue_cash_transfer(self, space_id, owner_faction, src_piece_idx, cash_count):
        if cash_count <= 0:
            return
        self._pending_cash_transfers.append({
            "space_id": int(space_id),
            "owner": int(owner_faction),
            "src_idx": int(src_piece_idx),
            "count": int(cash_count),
        })
        self._cash_transfer_waiting = True

    def _begin_pact_action_tracking(self):
        if "PactOfCaracas_Unshaded" in self.capabilities:
            self._pact_removed_bases_this_action = {1: 0, 2: 0}
        else:
            self._pact_removed_bases_this_action = None

    def _pact_blocks_opposition(self, acting_faction):
        if "PactOfCaracas_Unshaded" not in self.capabilities:
            return False
        if int(acting_faction) not in [1, 2]:
            return False
        return not self.same_player_control

    def _record_pact_base_removal(self, faction_idx):
        if "PactOfCaracas_Unshaded" not in self.capabilities:
            return
        if self._pact_removed_bases_this_action is None:
            return
        if faction_idx not in self._pact_removed_bases_this_action:
            return
        self._pact_removed_bases_this_action[faction_idx] += 1
        if self._pact_removed_bases_this_action[faction_idx] >= 2:
            self.capabilities.discard("PactOfCaracas_Unshaded")
            self._pact_removed_bases_this_action = None
            print(" -> Pact of Caracas: Capability cancelled (2 bases removed).")

    def _select_cash_holder_index(self, sp, faction_idx, preferred_idx=None):
        if preferred_idx is not None and int(sp.pieces[preferred_idx]) > 0:
            return int(preferred_idx)
        for idx in self._cash_piece_indices_for_faction(faction_idx):
            if int(sp.pieces[idx]) > 0:
                return int(idx)
        return None

    def _add_cash_marker(self, sp, faction_idx, preferred_idx=None, forced_holder_idx=None, owner_override=None):
        if forced_holder_idx is not None and int(sp.pieces[int(forced_holder_idx)]) > 0:
            holder_idx = int(forced_holder_idx)
        else:
            holder_idx = self._select_cash_holder_index(sp, faction_idx, preferred_idx=preferred_idx)
        if holder_idx is None:
            return False
        sp.cash_holders[holder_idx] += 1
        if hasattr(sp, "cash_owner_by_holder"):
            sp.cash_owner_by_holder[holder_idx] = int(faction_idx if owner_override is None else owner_override)
        self._refresh_space_cash_counts(sp)
        return True

    def _remove_cash_marker(self, sp, faction_idx):
        for idx in self._cash_piece_indices_for_faction(faction_idx):
            if int(sp.cash_holders[idx]) > 0:
                sp.cash_holders[idx] -= 1
                self._refresh_space_cash_counts(sp)
                return True
        return False

    def _transfer_cash_marker(self, sp, src_faction, dest_faction):
        if not self._remove_cash_marker(sp, src_faction):
            return False
        if not self._add_cash_marker(sp, dest_faction):
            return False
        return True

    def _move_cash_with_piece(self, src_sp, dest_sp, piece_idx):
        if int(src_sp.cash_holders[piece_idx]) <= 0:
            return
        owner = None
        if hasattr(src_sp, "cash_owner_by_holder"):
            owner = int(src_sp.cash_owner_by_holder[piece_idx])
        src_sp.cash_holders[piece_idx] -= 1
        dest_sp.cash_holders[piece_idx] += 1
        if owner is not None and hasattr(dest_sp, "cash_owner_by_holder"):
            if int(dest_sp.cash_owner_by_holder[piece_idx]) < 0:
                dest_sp.cash_owner_by_holder[piece_idx] = int(owner)
        if hasattr(src_sp, "cash_owner_by_holder") and int(src_sp.cash_holders[piece_idx]) <= 0:
            src_sp.cash_owner_by_holder[piece_idx] = -1
        self._refresh_space_cash_counts(src_sp)
        self._refresh_space_cash_counts(dest_sp)

    def _move_cash_between_piece_indices(self, sp, src_idx, dest_idx, count=1):
        moved = 0
        owner = None
        if hasattr(sp, "cash_owner_by_holder"):
            owner = int(sp.cash_owner_by_holder[int(src_idx)])
        for _ in range(int(count)):
            if int(sp.cash_holders[src_idx]) <= 0:
                break
            sp.cash_holders[src_idx] -= 1
            sp.cash_holders[dest_idx] += 1
            moved += 1
        if moved and hasattr(sp, "cash_owner_by_holder"):
            if owner is not None and owner >= 0 and int(sp.cash_owner_by_holder[int(dest_idx)]) < 0:
                sp.cash_owner_by_holder[int(dest_idx)] = int(owner)
            if int(sp.cash_holders[int(src_idx)]) <= 0:
                sp.cash_owner_by_holder[int(src_idx)] = -1
        if moved:
            self._refresh_space_cash_counts(sp)
        return moved

    def _move_pieces_with_cash(self, src_id, dest_id, faction_idx, piece_type, count):
        if count <= 0 or src_id == dest_id:
            return 0
        moved = 0
        piece_idx = self.board.get_piece_index(faction_idx, piece_type)
        src_sp = self.board.spaces[int(src_id)]
        dest_sp = self.board.spaces[int(dest_id)]
        for _ in range(int(count)):
            if int(src_sp.pieces[piece_idx]) <= 0:
                break
            src_sp.pieces[piece_idx] -= 1
            dest_sp.pieces[piece_idx] += 1
            self._move_cash_with_piece(src_sp, dest_sp, piece_idx)
            moved += 1
        if int(src_sp.pieces[piece_idx]) == 0 and int(src_sp.cash_holders[piece_idx]) > 0:
            while int(src_sp.cash_holders[piece_idx]) > 0:
                self._move_cash_with_piece(src_sp, dest_sp, piece_idx)
        src_sp.update_control()
        dest_sp.update_control()
        return moved

    def _can_place_casino(self, sp):
        if sp.type == 4:
            return False
        non_casino_bases = int(sp.govt_bases + sp.pieces[4] + sp.pieces[7])
        if non_casino_bases > 2:
            return False
        if int(sp.pieces[10]) >= 2:
            return False
        return sp.type in [0, 1, 2, 3]

    def _space_has_valid_cash_transfer(self, sp):
        owners = [f for f in range(4) if self._space_has_faction_pieces(sp, f) and self._space_cash_by_faction(sp, f) > 0]
        dests = [f for f in range(4) if self._space_has_faction_pieces(sp, f)]
        return bool(owners and dests)

    def _space_has_valid_cash_transfer_between_holders(self, sp):
        src_indices = [idx for idx in range(len(sp.cash_holders)) if int(sp.cash_holders[idx]) > 0]
        if not src_indices:
            return False
        dest_indices = [idx for idx in range(len(sp.pieces)) if int(sp.pieces[idx]) > 0]
        if not dest_indices:
            return False
        for src_idx in src_indices:
            for dest_idx in dest_indices:
                if int(dest_idx) != int(src_idx):
                    return True
        return False

    def _infer_cash_owner_from_holder_idx(self, sp, holder_idx):
        if hasattr(sp, "cash_owner_by_holder"):
            owner = int(sp.cash_owner_by_holder[int(holder_idx)])
            if owner >= 0:
                return owner
        return int(self._faction_for_piece_index(int(holder_idx)))

    def _transfer_cash_between_holders(self, sp, src_holder_idx, dest_holder_idx):
        src_holder_idx = int(src_holder_idx)
        dest_holder_idx = int(dest_holder_idx)
        if int(sp.cash_holders[src_holder_idx]) <= 0:
            return False
        if int(sp.pieces[dest_holder_idx]) <= 0:
            return False

        owner = self._infer_cash_owner_from_holder_idx(sp, src_holder_idx)
        sp.cash_holders[src_holder_idx] -= 1
        sp.cash_holders[dest_holder_idx] += 1
        if hasattr(sp, "cash_owner_by_holder"):
            sp.cash_owner_by_holder[dest_holder_idx] = int(owner)
        self._refresh_space_cash_counts(sp)
        return True

    def _shift_toward_active_support(self, sp):
        if sp.alignment == 2:
            if sp.support_active:
                sp.support_active = False
            else:
                sp.alignment = 0
        elif sp.alignment == 0:
            sp.alignment = 1
            sp.support_active = False
        elif sp.alignment == 1 and not sp.support_active:
            sp.support_active = True

    def _shift_toward_active_opposition(self, sp):
        if sp.alignment == 1:
            if sp.support_active:
                sp.support_active = False
            else:
                sp.alignment = 0
        elif sp.alignment == 0:
            sp.alignment = 2
            sp.support_active = False
        elif sp.alignment == 2 and not sp.support_active:
            sp.support_active = True

    def _has_valid_casino_move(self):
        for src in self.board.spaces:
            if int(src.pieces[10]) <= 0:
                continue
            for dest in self.board.spaces:
                if dest.id == src.id:
                    continue
                if self._can_place_casino(dest):
                    return True
        return False

    def _shortest_space_distances(self, start_id):
        dist = {int(start_id): 0}
        queue = deque([int(start_id)])
        while queue:
            cur = queue.popleft()
            for adj in self.board.spaces[cur].adj_ids:
                if adj in dist:
                    continue
                dist[adj] = dist[cur] + 1
                queue.append(adj)
        return dist

    def _has_guerrillas_within_range(self, dest_id, u, a, max_range):
        dist = self._shortest_space_distances(dest_id)
        for sp in self.board.spaces:
            if dist.get(sp.id, 999) <= max_range and (sp.pieces[u] + sp.pieces[a]) > 0:
                return True
        return False

    def _brac_remove_guerrilla(self, sp, faction_idx, prefer_active=False):
        if faction_idx == 1:
            u_idx, a_idx = 2, 3
            owner = 1
        elif faction_idx == 2:
            u_idx, a_idx = 5, 6
            owner = 2
        else:
            u_idx, a_idx = 8, 9
            owner = 3

        if prefer_active:
            if sp.pieces[a_idx] > 0:
                sp.pieces[a_idx] -= 1
                self.players[owner].available_forces[0] += 1
                return True
            if sp.pieces[u_idx] > 0:
                sp.pieces[u_idx] -= 1
                self.players[owner].available_forces[0] += 1
                return True
            return False

        if sp.pieces[u_idx] > 0:
            sp.pieces[u_idx] -= 1
            self.players[owner].available_forces[0] += 1
            return True
        if sp.pieces[a_idx] > 0:
            sp.pieces[a_idx] -= 1
            self.players[owner].available_forces[0] += 1
            return True
        return False

    def _piece_present_for_faction(self, sp, faction_idx):
        if faction_idx == 0:
            return int(sp.pieces[0] + sp.pieces[1]) > 0
        if faction_idx == 1:
            return int(sp.pieces[2] + sp.pieces[3]) > 0
        if faction_idx == 2:
            return int(sp.pieces[5] + sp.pieces[6]) > 0
        return int(sp.pieces[8] + sp.pieces[9]) > 0

    def _any_piece_present_for_faction(self, sp, faction_idx):
        """Check if ANY piece (guerrillas/cubes AND bases) of a faction is in the space.
        Per COIN 2018 rulebook, 'pieces' includes all faction components."""
        if faction_idx == 0:
            return int(sp.pieces[0] + sp.pieces[1] + sp.govt_bases) > 0
        if faction_idx == 1:
            return int(sp.pieces[2] + sp.pieces[3] + sp.pieces[4]) > 0
        if faction_idx == 2:
            return int(sp.pieces[5] + sp.pieces[6] + sp.pieces[7]) > 0
        return int(sp.pieces[8] + sp.pieces[9] + sp.pieces[10]) > 0

    def _menoyo_un_remove_piece(self, sp, opt):
        if opt == 0 and sp.pieces[0] > 0:
            sp.pieces[0] -= 1
            self.players[0].available_forces[0] += 1
            return True
        if opt == 1 and sp.pieces[1] > 0:
            sp.pieces[1] -= 1
            self.players[0].available_forces[1] += 1
            return True
        if opt == 2 and sp.govt_bases > 0:
            sp.govt_bases -= 1
            self.players[0].available_bases += 1
            return True
        if opt == 3 and sp.pieces[2] > 0:
            self.board.remove_piece(sp.id, 1, 0)
            self.players[1].available_forces[0] += 1
            return True
        if opt == 4 and sp.pieces[3] > 0:
            self.board.remove_piece(sp.id, 1, 1)
            self.players[1].available_forces[0] += 1
            return True
        if opt == 5 and sp.pieces[4] > 0:
            self.board.remove_piece(sp.id, 1, 2)
            self.players[1].available_bases += 1
            return True
        if opt == 6 and sp.pieces[8] > 0:
            self.board.remove_piece(sp.id, 3, 0)
            self.players[3].available_forces[0] += 1
            return True
        if opt == 7 and sp.pieces[9] > 0:
            self.board.remove_piece(sp.id, 3, 1)
            self.players[3].available_forces[0] += 1
            return True
        return False

    def _redeploy_government_deterministic(self):
        for sp in self.board.spaces:
            sp.update_control()

        # 6.4.1 Police: move Police to ECs or Govt-Controlled spaces (deterministic policy).
        police_dests = [sp.id for sp in self.board.spaces if sp.type == 4 or sp.controlled_by == 1]
        if not police_dests:
            police_dests = [3]
        police_dest = police_dests[0]

        for sp in self.board.spaces:
            if int(sp.pieces[1]) <= 0:
                continue
            if sp.id == police_dest:
                continue
            mv = int(sp.pieces[1])
            self._move_pieces_with_cash(sp.id, police_dest, 0, 1, mv)

        # 6.4.2 Troops: move Troops on ECs or in Provinces without Govt Bases.
        troop_dests = [sp.id for sp in self.board.spaces if sp.controlled_by == 1 and (sp.type == 0 or sp.govt_bases > 0)]
        if not troop_dests:
            troop_dests = [3]
        troop_dest = troop_dests[0]

        for sp in self.board.spaces:
            is_province = sp.type in [1, 2, 3]
            is_ec = sp.type == 4
            must_redeploy = is_ec or (is_province and sp.govt_bases == 0)
            if not must_redeploy or int(sp.pieces[0]) <= 0 or sp.id == troop_dest:
                continue
            mv = int(sp.pieces[0])
            self._move_pieces_with_cash(sp.id, troop_dest, 0, 0, mv)

        for sp in self.board.spaces:
            sp.update_control()

    def _march_source_ids(self, pending_op):
        if pending_op is None or pending_op.get("op") != "MARCH_SRC":
            return []
        dest = pending_op.get("dest")
        u = pending_op.get("u")
        a = pending_op.get("a")
        if dest is None or u is None or a is None:
            return []
        max_range = int(pending_op.get("max_range", 1))
        mafia = bool(pending_op.get("mafia"))
        borrowed_used = bool(pending_op.get("borrowed_used", False))
        sources = []
        if max_range > 1:
            dist = self._shortest_space_distances(dest)
        for s_id in range(self.num_spaces):
            if s_id == dest:
                continue
            sp = self.board.spaces[s_id]
            has_guerrillas = (sp.pieces[u] + sp.pieces[a]) > 0
            has_mafia = (mafia and not borrowed_used) and (sp.pieces[8] + sp.pieces[9]) > 0
            if not (has_guerrillas or has_mafia):
                continue
            if max_range > 1:
                if dist.get(s_id, 999) <= max_range:
                    sources.append(s_id)
            else:
                if s_id in self.board.spaces[dest].adj_ids:
                    sources.append(s_id)
        return sources

    def _march_move_piece(self, src, dest, piece_idx):
        if piece_idx in [2, 3]:
            faction_idx = 1
        elif piece_idx in [5, 6]:
            faction_idx = 2
        elif piece_idx in [8, 9]:
            faction_idx = 3
        else:
            return False
        piece_type = 0 if piece_idx in [2, 5, 8] else 1
        moved = self._move_pieces_with_cash(src, dest, faction_idx, piece_type, 1) > 0
        
        # El Che capability: First M26 March group flips underground
        if moved and piece_type == 0 and faction_idx == 1:
            if "ElChe_Unshaded" in self.capabilities and self._pending_op_target.get("moved", 0) == 0:
                # First group stays underground (capability effect)
                pass
            else:
                # Normal: flip to Active in City/EC
                sp_dest = self.board.spaces[int(dest)]
                if sp_dest.type in [0, 4]:
                    sp_dest.pieces[piece_idx] -= 1
                    sp_dest.pieces[piece_idx + 1] += 1
                    self._move_cash_between_piece_indices(sp_dest, piece_idx, piece_idx + 1, 1)
                    sp_dest.update_control()
        elif moved and piece_type == 0:
            # Non-M26: normal activation
            sp_dest = self.board.spaces[int(dest)]
            if sp_dest.type in [0, 4]:
                sp_dest.pieces[piece_idx] -= 1
                sp_dest.pieces[piece_idx + 1] += 1
                self._move_cash_between_piece_indices(sp_dest, piece_idx, piece_idx + 1, 1)
                sp_dest.update_control()
        return moved

    def _finish_march(self, player, pending_op):
        moved = int(pending_op.get("moved", 0))
        if not pending_op.get("mafia") and moved > 0:
            dest = pending_op.get("dest")
            if dest is not None and self.board.spaces[int(dest)].type == 4:
                cost = 0
            else:
                cost = 1
            player.resources = max(0, player.resources - cost)
            self._last_op_paid_cost = int(cost)

        self._pending_op_target = None
        if pending_op.get("mafia"):
            self._pending_mafia_offensive = None

        player.eligible = False
        self.ineligible_next_card.add(self.current_player_num)
        self.card_action_slot += 1
        self.phase = PHASE_CHOOSE_MAIN
        self._pending_main = None

        if not pending_op.get("limited"):
            self._pending_sa = True
            self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

    def _sweep_sources(self, pending_op):
        if pending_op is None or pending_op.get("op") != "SWEEP_SRC":
            return []
        dest = pending_op.get("dest")
        if dest is None:
            return []
        allow_police = bool(pending_op.get("allow_police"))
        sources = []
        for s_id in self.board.spaces[int(dest)].adj_ids:
            sp = self.board.spaces[s_id]
            if int(sp.pieces[0]) > 0 or (allow_police and int(sp.pieces[1]) > 0):
                sources.append(s_id)
        return sources

    def _garrison_sources(self, pending_op):
        if pending_op is None or pending_op.get("op") != "GARRISON_SRC":
            return []
        dest = pending_op.get("dest")
        if dest is None:
            return []
        sources = []
        for s_id in self.board.spaces[int(dest)].adj_ids:
            sp = self.board.spaces[s_id]
            if int(sp.pieces[1]) > 0:
                sources.append(s_id)
        return sources

    def _sweep_reveal_only(self, dest):
        sp = self.board.spaces[int(dest)]
        rev = 0
        cubes = int(sp.pieces[0] + sp.pieces[1])
        for idx in [2, 5, 8]:
            h = int(sp.pieces[idx])
            tr = h if sp.type in [0, 2, 4] else min(h, cubes)
            if tr > 0:
                sp.pieces[idx] -= tr
                sp.pieces[idx + 1] += tr
                rev += tr
                self._move_cash_between_piece_indices(sp, idx, idx + 1, tr)
        print(f" -> Revealed {rev}")
        sp.update_control()

    def _finish_sweep(self, player, pending_op):
        dest = pending_op.get("dest")
        if dest is None:
            raise Exception("Sweep finish missing destination")
        self._sweep_reveal_only(dest)

        player.resources = max(0, int(player.resources) - self.get_govt_cost())
        self._last_op_paid_cost = int(self.get_govt_cost())

        self._pending_op_target = None
        if pending_op.get("limited"):
            player.eligible = False
            self.ineligible_next_card.add(self.current_player_num)
            self.card_action_slot += 1
            self.phase = PHASE_CHOOSE_MAIN
            self._pending_main = None
            return

        if "Masferrer_Shaded" in self.capabilities:
            sp = self.board.spaces[int(dest)]
            if sum(sp.pieces[2:11]) > 0:
                self._sa_restrict_op = OP_ASSAULT
                self._sa_restrict_space = int(dest)
                self._sa_free = True

        self._pending_sa = True
        self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

    def _finish_garrison(self, player, pending_op):
        player.resources = max(0, int(player.resources) - self.get_govt_cost())
        self._last_op_paid_cost = int(self.get_govt_cost())
        self._pending_op_target = None
        if pending_op.get("limited"):
            player.eligible = False
            self.ineligible_next_card.add(self.current_player_num)
            self.card_action_slot += 1
            self.phase = PHASE_CHOOSE_MAIN
            self._pending_main = None
            return

        self._pending_sa = True
        self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY

    def draw_next_card(self):
        while True:
            card = self.deck.draw()
            if card is None: 
                self.deck_empty = True
                self.next_card = None  # No more cards
                return False 
            if card.is_propaganda:
                self.current_card = card
                self.next_card = self.deck.peek()  # Peek at next card
                self.propaganda_cards_played += 1
                self._propaganda_in_progress = True
                self._propaganda_final_round = self.propaganda_cards_played >= 4
                winner = self._propaganda_victory_check()
                if winner != -1:
                    self.deck_empty = True
                    self._propaganda_in_progress = False
                    self.next_card = None
                    return False

                if not self._propaganda_final_round:
                    self._propaganda_resources_phase()

                self._propaganda_us_alliance_test()
                self._pending_propaganda = {"step": "CIVIC_ACTION"}
                self.current_player_num = 0
                self.phase = PHASE_CHOOSE_TARGET_SPACE

                if not self._propaganda_civic_action_targets():
                    self._propaganda_finish_after_civic_action()
                return False
            else:
                self.current_card = card
                self.next_card = self.deck.peek()  # Peek at next card
                # 2018 baseline: factions are Eligible at the start of each new card,
                # unless a prior effect made them Ineligible through this card.
                for p in self.players:
                    p.eligible = True
                for idx in list(self.ineligible_next_card):
                    if 0 <= idx < len(self.players):
                        self.players[idx].eligible = False
                self.ineligible_next_card.clear()
                for idx in list(self.ineligible_through_next_card):
                    if 0 <= idx < len(self.players):
                        self.players[idx].eligible = False
                self.ineligible_through_next_card.clear()
                self.factions_acted_this_card = 0
                self.card_action_slot = 0
                self._card_order_index = 0
                self.card_first_actor = None
                self.card_second_actor = None
                self.card_first_action = None
                self._pending_sa = None
                self._sa_free = False
                self._sa_from_limited_ops = False
                self._launder_used_this_card = False
                self._pending_launder = None
                self._launder_actor = None
                self._launder_free = False
                self._last_op_paid_cost = 0
                self._last_op = None
                self._last_op_space = None
                self._sa_restrict_op = None
                self._sa_restrict_space = None
                self.rounds_taken = getattr(self, 'rounds_taken', 0) + 1
                print(f"\n>>> NEW CARD: {card.name} (Order: {[self.factions_list[i] for i in card.faction_order]})")
                return True

    def _any_cash_for_faction(self, faction_idx):
        for sp in self.board.spaces:
            if self._space_cash_by_faction(sp, faction_idx) > 0:
                return True
        return False

    def _launder_provider_factions(self):
        return [f for f in range(4) if self._any_cash_for_faction(f)]

    def _launder_cash_spaces(self, faction_idx):
        return [sp.id for sp in self.board.spaces if self._space_cash_by_faction(sp, faction_idx) > 0]

    def _maybe_start_launder(self):
        if self._launder_used_this_card:
            return False
        if int(self._last_op_paid_cost) <= 0:
            return False
        if not self._launder_provider_factions():
            return False
        self._pending_launder = {"stage": "PROVIDER"}
        self._launder_actor = int(self.current_player_num)
        self.phase = PHASE_CHOOSE_TARGET_FACTION
        return True

    def update_turn_pointer(self):
        if self.card_action_slot >= 2:
            if not self.draw_next_card(): return 
        found = False
        for i in range(self._card_order_index, len(self.current_card.faction_order)):
            faction_idx = self.current_card.faction_order[i]
            if self.players[faction_idx].eligible:
                self.current_player_num = faction_idx
                self._card_order_index = i + 1
                if self.card_action_slot == 0 and self.card_first_actor is None:
                    self.card_first_actor = faction_idx
                if self.card_action_slot == 1 and self.card_second_actor is None:
                    self.card_second_actor = faction_idx
                found = True
                break
        if not found:
            print(" -> No eligible factions left. Next Card.")
            if self.draw_next_card(): self.update_turn_pointer()


    def step(self, action):
        return self._internal_step(action)

    @property
    def observation(self):
        # Header (length 15)
        # 0: phase (0-2)
        # 1: current player index (0-3)
        # 2: factions acted this card (0-2)
        # 3: US alliance level (0-2; Firm/Reluctant/Embargoed)
        # 4: current card id (0-48)
        # 5: pending main (-1 none, 0 event, 1 ops)
        # 6: current player resources
        # 7: deck empty flag
        # 8: eligible flag for current player
        # 9: Aid track (0-49)
        # 10: Total Support (derived)
        # 11: Opposition + Bases (derived)
        # 12: DR Pop + Bases (derived)
        # 13: Open Casinos (derived)
        # 14: next card id (0-48, 0 if none - peek ahead mechanic)
        self._refresh_campaign_tracks()
        header = np.zeros((self._obs_header_size,), dtype=np.float32)
        header[0] = float(self.phase)
        header[1] = float(self.current_player_num)
        header[2] = float(self.factions_acted_this_card)
        header[3] = float(self.us_alliance)
        header[4] = float(self.current_card.id if self.current_card is not None else 0)
        if self._pending_main is None:
            header[5] = -1.0
        elif self._pending_main == MAIN_EVENT:
            header[5] = 0.0
        elif self._pending_main == MAIN_OPS:
            header[5] = 1.0
        else:
            header[5] = -1.0
        header[6] = float(self.players[self.current_player_num].resources) if hasattr(self, 'players') and self.players else 0.0
        header[7] = 1.0 if self.deck_empty else 0.0
        header[8] = 1.0 if self.players[self.current_player_num].eligible else 0.0
        header[9] = float(self.aid)

        header[10] = float(self.total_support_track)
        header[11] = float(self.opposition_plus_bases_track)
        header[12] = float(self.dr_pop_plus_bases_track)
        header[13] = float(self.open_casinos_track)
        header[14] = float(self.next_card.id if self.next_card is not None else 0)

        # Per-space features (space_feature_size = 13)
        # 11 piece slots + terror + alignment
        spaces = np.zeros((self.num_spaces, self.space_feature_size), dtype=np.float32)
        for i, sp in enumerate(self.board.spaces):
            spaces[i, 0:11] = sp.pieces[0:11]
            spaces[i, 11] = float(sp.terror)
            spaces[i, 12] = float(sp.alignment)

        return np.concatenate([header, spaces.flatten()]).astype(np.float32)
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            self._seed(seed)
            
        scenario = "standard"
        if options and "scenario" in options:
            scenario = options["scenario"]

        self.deck = Deck(scenario=scenario); self.board = Board(); self.players = []
        for i, n in enumerate(self.factions_list):
            f = Faction(i, n)
            if n == "GOVT":
                f.resources = 15
            elif n == "M26":
                f.resources = 10
            elif n == "DR":
                f.resources = 5
            else:
                f.resources = 15
            self.players.append(f)

        # 2018 campaign starting tracks (from playbook)
        self.set_aid(15)
        self.set_us_alliance(US_ALLIANCE_FIRM)
        p = self.players[0]
        for _ in range(6):
            self.board.add_piece(3, 0, 0); p.available_forces[0] -= 1
        for _ in range(4):
            self.board.add_piece(3, 0, 1); p.available_forces[1] -= 1
        self.current_player_num = 0; self.rounds_taken = 0; self.done = False; self.capabilities = set()
        self.deck_empty = False
        self.propaganda_cards_played = 0
        self.final_victory_margins_result = None
        self.final_victory_ranking_result = None
        self.phase = PHASE_CHOOSE_MAIN
        self._pending_main = None
        self._pending_op_target = None
        self.keep_eligible_this_action = False
        self._pending_cash_transfers = deque()
        self._cash_transfer_waiting = False
        self._cash_transfer_active = False
        self._cash_transfer_return_player = None
        self._cash_transfer_return_phase = None
        self._cash_transfer_return_advance = False
        self.ineligible_through_next_card = set()
        self.ineligible_next_card = set()
        self.card_first_action = None
        self._pending_event_target = None
        self._pending_event_faction = None
        self._pending_event_option = None
        self._propaganda_in_progress = False
        self._propaganda_final_round = False
        self._pending_propaganda = None
        self._pending_mafia_offensive = None
        self._pact_removed_bases_this_action = None
        self._refresh_campaign_tracks()
        self.draw_next_card(); self.update_turn_pointer()
        self.board.env = self
        return self.observation, {}
        
    def _seed(self, seed=None):
        random.seed(seed)
        np.random.seed(seed)
    def render(self, mode='human', close=False):
        if close: return
        print(f"\n--- Round {self.rounds_taken} [{self.factions_list[self.current_player_num]}] Res:{self.players[self.current_player_num].resources} | Propaganda: {self.propaganda_cards_played}/4 ---")
        if self.current_card: print(f"Card: {self.current_card.name}")
        out = f"{'Space':<15} | {'Govt':<5} | {'M26(U:A)':<8} | {'DR(U:A)':<8} | {'Syn(U:A)':<8}\n" + "-" * 70 + "\n"
        for s in self.board.spaces:
            p = s.pieces; m26 = f"{p[2]}:{p[3]}"; dr = f"{p[5]}:{p[6]}"; syn = f"{p[8]}:{p[9]}"
            if sum(p) + s.terror > 0:
                out += f"{s.name:<15} | {p[0]}/{p[1]:<3} | {m26:<8} | {dr:<8} | {syn:<8}\n"
        print(out)
