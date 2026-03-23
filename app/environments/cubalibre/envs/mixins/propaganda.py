import numpy as np
import random
import math
from collections import deque
from ..classes import *
from ..constants import *
from ..data import EVENT_DECK_DATA
from ..events import resolve_event, _free_ambush_against_govt, _free_ambush_against_govt_bases_first, _shift_alignment

class PropagandaMixin:
    def resolve_propaganda(self):
        print(f"\n{'-'*30}\n!!! PROPAGANDA ROUND !!!\n{'-'*30}")
        final_round = self.propaganda_cards_played >= 4

        # 6.1 Victory Phase (7.2)
        winner = self._propaganda_victory_check()

        if winner != -1:
            print(f"*** {self.factions_list[winner]} WINS! ***")
            return True

        # Final Propaganda: skip Resources Phase, proceed to Support Phase only.
        if not final_round:
            self._propaganda_resources_phase()

        # 6.3 Support Phase (partial)
        # 6.3.1 US Alliance test: If Total Support <= 18, worsen 1 level (if possible) and Aid -10 (min 0), even if already Embargoed.
        self._propaganda_us_alliance_test()

        # 6.3.2 Civic Action (deterministic spend)
        govt = self.players[0]
        for sp in self.board.spaces:
            if sp.type not in [0, 1, 2, 3]:
                continue
            sp.update_control()
            if sp.controlled_by != 1:
                continue
            if int(sp.pieces[0]) <= 0 or int(sp.pieces[1]) <= 0:
                continue
            while govt.resources >= 4 and (sp.terror > 0 or not (sp.alignment == 1 and sp.support_active)):
                if sp.terror > 0:
                    sp.terror -= 1
                else:
                    self._shift_toward_active_support(sp)
                govt.resources -= 4
            sp.update_control()

        # 6.3.3 Agitation
        self._propaganda_agitation()

        # 6.3.4 Expat Backing
        self._propaganda_expat_backing()

        # 6.3.5 Game End? The final Propaganda round omits Redeploy and Reset (6.4-6.5).
        if final_round:
            self.final_victory_margins_result = self.victory_margins()
            self.final_victory_ranking_result = self.final_victory_ranking()
            winner_idx = self.final_victory_ranking_result[0]
            margins = self.final_victory_margins_result
            print(f"\n{'='*40}")
            print(f"  FINAL PROPAGANDA — {self.factions_list[winner_idx]} WINS!")
            print(f"  Margins: GOVT={margins[0]:+d}  M26={margins[1]:+d}  DR={margins[2]:+d}  SYN={margins[3]:+d}")
            print(f"  Ranking: {[self.factions_list[f] for f in self.final_victory_ranking_result]}")
            print(f"{'='*40}")
            return False

        # 6.4 Redeploy Phase (partial)
        if self.propaganda_cards_played < 4:
            self._redeploy_government_deterministic()

            # 6.4.3 Optional other Troops redeploy: left as no-op for now.

        self._propaganda_cleanup_and_reset()

        return (winner != -1)


    def _propaganda_victory_check(self):
        self._refresh_campaign_tracks()
        govt_wins = (self.total_support_track > 18) and all((sp.type != 0) or (sp.alignment == 1 and sp.support_active) for sp in self.board.spaces)
        m26_wins = self.opposition_plus_bases_track > 15
        dr_wins = self.dr_pop_plus_bases_track > 9
        syn_wins = (self.open_casinos_track > 7) and (self.players[3].resources > 30)

        if govt_wins:
            return 0
        if m26_wins:
            return 1
        if dr_wins:
            return 2
        if syn_wins:
            return 3
        return -1


    def _propaganda_expat_backing(self):
        for sp in self.board.spaces:
            sp.update_control()
            if sp.support_active and sp.alignment in [1, 2]:
                continue
            if sp.controlled_by not in [0, 3]:
                continue
            self.op_rally_dr(sp.id)
            sp.update_control()
            break


    def _propaganda_redeploy_police_sources(self):
        return [sp.id for sp in self.board.spaces if int(sp.pieces[1]) > 0]


    def _propaganda_redeploy_police_destinations(self):
        for sp in self.board.spaces:
            sp.update_control()
        dests = [sp.id for sp in self.board.spaces if sp.type == 4 or sp.controlled_by == 1]
        if not dests:
            dests = [3]
        return dests


    def _propaganda_redeploy_troop_mandatory_sources(self):
        sources = []
        for sp in self.board.spaces:
            is_ec = sp.type == 4
            is_province = sp.type in [1, 2, 3]
            if (is_ec or (is_province and sp.govt_bases == 0)) and int(sp.pieces[0]) > 0:
                sources.append(sp.id)
        return sources


    def _propaganda_redeploy_troop_optional_sources(self):
        mandatory = set(self._propaganda_redeploy_troop_mandatory_sources())
        sources = []
        for sp in self.board.spaces:
            if int(sp.pieces[0]) > 0 and sp.id not in mandatory:
                sources.append(sp.id)
        return sources


    def _propaganda_redeploy_troop_destinations(self):
        for sp in self.board.spaces:
            sp.update_control()
        dests = [sp.id for sp in self.board.spaces if sp.controlled_by == 1 and (sp.type == 0 or sp.govt_bases > 0)]
        if not dests:
            dests = [3]
        return dests


    def _propaganda_start_redeploy(self):
        police_sources = self._propaganda_redeploy_police_sources()
        mandatory_sources = self._propaganda_redeploy_troop_mandatory_sources()
        optional_sources = self._propaganda_redeploy_troop_optional_sources()
        if not police_sources and not mandatory_sources and not optional_sources:
            self._propaganda_finish_redeploy()
            return

        self._pending_propaganda = {"step": "REDEPLOY_MENU"}
        self.current_player_num = 0
        self.phase = PHASE_PROPAGANDA_REDEPLOY_MENU


    def _propaganda_finish_redeploy(self):
        self._pending_propaganda = None
        self._propaganda_in_progress = False
        self.phase = PHASE_CHOOSE_MAIN
        self._propaganda_cleanup_and_reset()
        self.draw_next_card()
        self.update_turn_pointer()


    def _propaganda_finish_after_expat(self):
        self._pending_propaganda = None
        self._propaganda_in_progress = False
        self.phase = PHASE_CHOOSE_MAIN

        if self._propaganda_final_round:
            self.final_victory_margins_result = self.victory_margins()
            self.final_victory_ranking_result = self.final_victory_ranking()
            self.deck_empty = True
            self._propaganda_final_round = False
            return

        self._propaganda_final_round = False
        self._propaganda_start_redeploy()


    def _propaganda_cleanup_and_reset(self):
        expiring_capabilities = [
            "ArmoredCars_Shaded",
            "Guantanamo_Shaded",
            "SIM_Shaded",
            "Masferrer_Shaded",
            "Mosquera_Shaded",
            "MAP_Shaded",
            "Raul_Shaded",
            "GuerrillaLife_Unshaded",
        ]
        for cap in expiring_capabilities:
            if cap in self.capabilities:
                self.capabilities.remove(cap)

        for p in self.players:
            p.eligible = True
        for sp in self.board.spaces:
            sp.terror = 0
            sp.sabotage = False
            sp.pieces[2] += sp.pieces[3]; sp.pieces[3] = 0
            sp.pieces[5] += sp.pieces[6]; sp.pieces[6] = 0
            sp.pieces[8] += sp.pieces[9]; sp.pieces[9] = 0
            if int(sp.cash_holders[3]) > 0:
                self._move_cash_between_piece_indices(sp, 3, 2, int(sp.cash_holders[3]))
            if int(sp.cash_holders[6]) > 0:
                self._move_cash_between_piece_indices(sp, 6, 5, int(sp.cash_holders[6]))
            if int(sp.cash_holders[9]) > 0:
                self._move_cash_between_piece_indices(sp, 9, 8, int(sp.cash_holders[9]))
            if getattr(sp, "closed_casinos", 0) > 0:
                sp.pieces[10] += int(sp.closed_casinos)
                sp.closed_casinos = 0
            sp.update_control()


    def _propaganda_civic_action_targets(self):
        govt = self.players[0]
        if govt.resources < 4:
            return []
        targets = []
        for sp in self.board.spaces:
            if sp.type not in [0, 1, 2, 3]:
                continue
            sp.update_control()
            if sp.controlled_by != 1:
                continue
            if int(sp.pieces[0]) <= 0 or int(sp.pieces[1]) <= 0:
                continue
            if sp.terror > 0 or not (sp.alignment == 1 and sp.support_active):
                targets.append(sp.id)
        return targets


    def _propaganda_finish_after_civic_action(self):
        self._pending_propaganda = None
        self._propaganda_in_progress = False
        self.phase = PHASE_CHOOSE_MAIN

        agitation_targets = self._propaganda_agitation_targets()
        if agitation_targets:
            self._pending_propaganda = {"step": "AGITATION"}
            self.current_player_num = 1
            self.phase = PHASE_CHOOSE_TARGET_SPACE
            return
        expat_targets = self._propaganda_expat_targets()
        if expat_targets:
            self._pending_propaganda = {"step": "EXPAT_BACKING"}
            self.current_player_num = 2
            self.phase = PHASE_CHOOSE_TARGET_SPACE
            return

        self._propaganda_finish_after_expat()


    def _propaganda_resources_phase(self):
        # 6.2.1 Government Earnings: Sabotage ECs where M26+DR guerrillas outnumber cubes; then add econ of unsabotaged ECs + Aid.
        for sp in self.board.spaces:
            if sp.type == 4:
                insurgent_g = int(sp.pieces[2] + sp.pieces[3] + sp.pieces[5] + sp.pieces[6])
                cubes = int(sp.pieces[0] + sp.pieces[1])
                if insurgent_g > cubes:
                    sp.sabotage = True

        econ_unsabotaged = 0
        for sp in self.board.spaces:
            if sp.type == 4 and not sp.sabotage:
                econ_unsabotaged += int(sp.econ_value)

        govt_income = int(econ_unsabotaged + int(self.aid))
        self.players[0].resources = min(49, int(self.players[0].resources) + govt_income)

        # 6.2.2 Insurgent Earnings
        m26_bases = sum(int(sp.pieces[4]) for sp in self.board.spaces)
        self.players[1].resources = min(49, int(self.players[1].resources) + m26_bases)

        dr_spaces_with_pieces = 0
        for sp in self.board.spaces:
            if int(sp.pieces[5] + sp.pieces[6] + sp.pieces[7]) > 0:
                dr_spaces_with_pieces += 1
        self.players[2].resources = min(49, int(self.players[2].resources) + dr_spaces_with_pieces)

        syn_income = 0
        for sp in self.board.spaces:
            syn_g = int(sp.pieces[8] + sp.pieces[9])
            police = int(sp.pieces[1])
            if syn_g <= police:
                continue
            if sp.type == 0:
                syn_income += int(sp.population)
            elif sp.type == 4 and not sp.sabotage:
                syn_income += int(sp.econ_value)
        syn_income += 2 * self.open_casinos_track
        self.players[3].resources = min(49, int(self.players[3].resources) + int(syn_income))

        # 6.2.3 The Skim
        santo_blocks_skim = "Trafficante_Shaded" in self.capabilities
        for sp in self.board.spaces:
            if int(sp.pieces[10]) <= 0:
                continue

            if santo_blocks_skim and int(sp.pieces[8]) > 0:
                continue

            sp.update_control()
            if sp.controlled_by in [0, 4]:
                continue

            transfer = min(2, int(self.players[3].resources))
            if transfer <= 0:
                continue
            self.players[3].resources = int(self.players[3].resources) - transfer
            self.players[sp.controlled_by - 1].resources = min(49, int(self.players[sp.controlled_by - 1].resources) + transfer)

        # 6.2.4 Cash Deposits
        for faction_idx in [1, 2, 0, 3]:
            for sp in self.board.spaces:
                cash_count = self._space_cash_by_faction(sp, faction_idx)
                if cash_count <= 0:
                    continue

                for _ in range(cash_count):
                    self._remove_cash_marker(sp, faction_idx)

                    if faction_idx == 0:
                        if self.players[0].available_bases > 0:
                            sp.govt_bases += 1
                            self.players[0].available_bases -= 1
                        else:
                            self.players[0].resources = min(49, int(self.players[0].resources) + 6)
                    elif faction_idx == 1:
                        if self.players[1].available_bases > 0:
                            sp.pieces[4] += 1
                            self.players[1].available_bases -= 1
                        else:
                            self.players[1].resources = min(49, int(self.players[1].resources) + 6)
                    elif faction_idx == 2:
                        if self.players[2].available_bases > 0:
                            sp.pieces[7] += 1
                            self.players[2].available_bases -= 1
                        else:
                            self.players[2].resources = min(49, int(self.players[2].resources) + 6)
                    else:
                        if getattr(sp, "closed_casinos", 0) > 0:
                            sp.closed_casinos -= 1
                            sp.pieces[10] += 1
                        elif self.players[3].available_bases > 0:
                            sp.pieces[10] += 1
                            self.players[3].available_bases -= 1
                        else:
                            self.players[3].resources = min(49, int(self.players[3].resources) + 6)

                    sp.update_control()


    def _propaganda_us_alliance_test(self):
        # 6.3.1 US Alliance test
        if self.total_support_track <= 18:
            if self.us_alliance < US_ALLIANCE_EMBARGOED:
                self.shift_us_alliance(1)
            self.shift_aid(-10)


    def _propaganda_agitation(self):
        m26 = self.players[1]
        for sp in self.board.spaces:
            if sp.type not in [0, 1, 2, 3]:
                continue
            sp.update_control()
            if sp.controlled_by != 2:
                continue
            while m26.resources >= 1 and (sp.terror > 0 or not (sp.alignment == 2 and sp.support_active)):
                if sp.terror > 0:
                    sp.terror -= 1
                else:
                    self._shift_toward_active_opposition(sp)
                m26.resources -= 1
            sp.update_control()


    def _propaganda_agitation_targets(self):
        m26 = self.players[1]
        if m26.resources < 1:
            return []
        targets = []
        for sp in self.board.spaces:
            if sp.type not in [0, 1, 2, 3]:
                continue
            sp.update_control()
            if sp.controlled_by != 2:
                continue
            if sp.terror > 0 or not (sp.alignment == 2 and sp.support_active):
                targets.append(sp.id)
        return targets


    def _propaganda_finish_after_agitation(self):
        self._pending_propaganda = None
        self._propaganda_in_progress = False
        self.phase = PHASE_CHOOSE_MAIN

        expat_targets = self._propaganda_expat_targets()
        if expat_targets:
            self._pending_propaganda = {"step": "EXPAT_BACKING"}
            self.current_player_num = 2
            self.phase = PHASE_CHOOSE_TARGET_SPACE
            return

        self._propaganda_finish_after_expat()


    def _propaganda_expat_targets(self):
        targets = []
        for sp in self.board.spaces:
            sp.update_control()
            if sp.support_active and sp.alignment in [1, 2]:
                continue
            if sp.controlled_by not in [0, 3]:
                continue
            targets.append(sp.id)
        return targets
