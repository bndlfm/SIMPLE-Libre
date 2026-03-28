import numpy as np
import random
import math
from collections import deque
from ..classes import *
from ..constants import *
from ..data import EVENT_DECK_DATA
from ..events import resolve_event, _free_ambush_against_govt, _free_ambush_against_govt_bases_first, _shift_alignment

class StepMixin:
    def _internal_step(self, action):
        if self.deck_empty:
             return self.observation, 0.0, True, False, {"rewards": [0.0] * self.n_players}
        reward = [0.0] * self.n_players; done = False
        player = self.players[self.current_player_num]

        # Auto-skip ineligible players (COIN rules: they are simply skipped,
        # no action taken, no resources gained).  This catches both MaskablePPO
        # and selfplay opponents, which use different mask paths.
        if self.phase == PHASE_CHOOSE_MAIN and not player.eligible:
            print(f"  (auto-skip ineligible {player.name} in step())")
            self.card_action_slot += 1
            self.update_turn_pointer()
            return self.observation, 0.0, self.deck_empty, False, {"rewards": reward}

        advance_turn = True
        self.keep_eligible_this_action = False
        if self._cash_transfer_waiting and not self._cash_transfer_active and self.phase == PHASE_CHOOSE_MAIN:
            pending = self._pending_cash_transfers[0]
            if self._cash_transfer_return_player is None:
                self._cash_transfer_return_player = self.current_player_num
                self._cash_transfer_return_phase = self.phase
                self._cash_transfer_return_advance = advance_turn
            self.current_player_num = int(pending.get("owner"))
            self.phase = PHASE_CHOOSE_TARGET_PIECE
            self._cash_transfer_active = True
            player = self.players[self.current_player_num]
            advance_turn = False

        # check move legality
        if self.legal_actions[action] == 0:
            print(f"!!! ILLEGAL ACTION: {action} (phase={self.phase})")
            reward[self.current_player_num] = -1.0
            if self.card_action_slot == 0 and self.card_first_action is None:
                self.card_first_action = "ILLEGAL"
            player.eligible = False
            self.ineligible_next_card.add(self.current_player_num)
            self.card_action_slot += 1
            self.phase = PHASE_CHOOSE_MAIN
        else:
            cost = 0
            # Phase 0: main choice
            if self.phase == PHASE_CHOOSE_MAIN:
                if action == self._limited_main_action_id:
                    self._pending_main = MAIN_OPS
                    self._begin_pact_action_tracking()
                    self.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
                    advance_turn = False
                else:
                    main_choice = action - self._main_action_base
                    if main_choice == MAIN_PASS:
                        print(f"{player.name}: PASS")
                        # 2.3.3 Passing: gain Resources (Govt +3, others +1),
                        # do not count as one of the 1st/2nd executing factions,
                        # and remain eligible for the next card.
                        gained = 3 if player.name == "GOVT" else 1
                        player.resources = min(49, int(player.resources) + gained)
                        player.eligible = False
                    elif main_choice == MAIN_EVENT:
                        self._pending_main = MAIN_EVENT
                        if self.card_action_slot == 0 and self.card_first_action is None:
                            self.card_first_action = "EVENT"
                        self._begin_pact_action_tracking()
                        self.phase = PHASE_CHOOSE_EVENT_SIDE
                        advance_turn = False
                    elif main_choice == MAIN_OPS:
                        self._pending_main = MAIN_OPS
                        if self.card_action_slot == 0 and self.card_first_action is None:
                            self.card_first_action = "OPS"
                        self._begin_pact_action_tracking()
                        self.phase = PHASE_CHOOSE_OP_ACTION
                        advance_turn = False
                    else:
                        raise Exception(f"Invalid main choice: {main_choice}")

            elif self.phase == PHASE_PROPAGANDA_REDEPLOY_MENU:
                main_choice = action - self._main_action_base
                mandatory_sources = self._propaganda_redeploy_troop_mandatory_sources()
                if main_choice == MAIN_PASS:
                    if mandatory_sources:
                        raise Exception("Cannot skip mandatory troop redeploy")
                    self._propaganda_finish_redeploy()
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if main_choice == MAIN_EVENT:
                    if not self._propaganda_redeploy_police_sources():
                        raise Exception("No police available to redeploy")
                    self._pending_propaganda = {"step": "REDEPLOY_POLICE_SRC"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif main_choice == MAIN_OPS:
                    if mandatory_sources:
                        self._pending_propaganda = {"step": "REDEPLOY_TROOPS_MANDATORY_SRC"}
                    else:
                        if not self._propaganda_redeploy_troop_optional_sources():
                            raise Exception("No troops available to redeploy")
                        self._pending_propaganda = {"step": "REDEPLOY_TROOPS_OPTIONAL_SRC"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                else:
                    raise Exception(f"Invalid redeploy choice: {main_choice}")

            # Phase 1: event side
            elif self.phase == PHASE_CHOOSE_EVENT_SIDE:
                # resolve chosen event side
                side_choice = action - self._event_side_base
                play_shaded = (side_choice == EVENT_SHADED)
                card_id = self.current_card.id
                # Acting faction is ineligible for the remainder of the current card once it commits to the event.
                player.eligible = False

                # Events that require an explicit target-space selection (agent-driven).
                if card_id == 44 and not play_shaded:
                    # Rebel Air Force (Un): 26July or DR Guerrilla free Ambushes.
                    self._pending_event_faction = {"event": "REBEL_AIR_FORCE_UN_FACTION", "allowed": [1, 2]}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                elif card_id == 44 and play_shaded:
                    # Rebel Air Force (Sh): Select 26July or DR and transfer 1 die roll Resources.
                    self._pending_event_faction = {"event": "REBEL_AIR_FORCE_SH", "allowed": [1, 2]}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                elif card_id == 41 and play_shaded:
                    # Fat Butcher (Sh): Syndicate free Ambushes and opens 1 closed Casino.
                    self._pending_event_target = {"event": "FAT_BUTCHER_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 41 and not play_shaded:
                    # Fat Butcher (Un): Close 1 Casino or Aid -8.
                    any_open = any(sp.pieces[10] > 0 for sp in self.board.spaces)
                    allowed = [1]  # option 1 = Aid -8 is always allowed
                    if any_open:
                        allowed = [0, 1]  # option 0 = Close Casino
                    self._pending_event_option = {"event": "FAT_BUTCHER_UN", "allowed": allowed}
                    self.phase = PHASE_CHOOSE_EVENT_OPTION
                    advance_turn = False
                elif card_id == 42 and not play_shaded:
                    # Llano (Un): Place a 26July Base and any Guerrilla in a City - choose space first.
                    self._pending_event_target = {"event": "LLANO_UN"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 42 and play_shaded:
                    # Llano (Sh): Select a City. Remove Opposition.
                    self._pending_event_target = {"event": "LLANO_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 1 and not play_shaded:
                    # Armored Cars (Un): 26July or DR free Marches into a space and free Ambushes there (even if Active).
                    self._pending_event_faction = {"event": "ARMORED_CARS_UN_FACTION", "allowed": [1, 2]}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                elif card_id == 6 and not play_shaded:
                    # Sanchez Mosquera (Un): Remove all Troops from a Mountain space.
                    self._pending_event_target = {"event": "MOSQUERA_UN"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 12 and not play_shaded:
                    # BRAC (Un): Remove any 2 Guerrillas.
                    self._pending_event_target = {"event": "BRAC_UN", "count": 0}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 12 and play_shaded:
                    # BRAC (Sh): Place 1 Police anywhere. Add lesser of +6 or Aid to Govt Resources.
                    self._pending_event_target = {"event": "BRAC_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 43 and not play_shaded:
                    # Mafia Offensive (Un): 26July or DR executes a free LimOp.
                    self._pending_event_faction = {"event": "MAFIA_OFFENSIVE_UN_FACTION", "allowed": [1, 2]}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                elif card_id == 44 and play_shaded:
                    # Rebel Air Force (Sh): Select 26July or DR and transfer 1 die roll Resources.
                    self._pending_event_faction = {"event": "REBEL_AIR_FORCE_SH", "allowed": [1, 2]}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                elif card_id == 21 and play_shaded:
                    # Fangio (Sh): In 2 spaces with any Casinos, open a closed Casino or place 1 Cash with a Guerrilla or cube.
                    self._pending_event_target = {"event": "FANGIO_SH", "stage": "SPACE1", "picked": []}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 3 and not play_shaded:
                    # Eulogio Cantillo (Un): Select a space with Troops. A Faction free Marches all its Guerrillas out, then flips them Underground.
                    self._pending_event_target = {"event": "CANTILLO_UN", "stage": "SPACE"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 8:
                    if not play_shaded:
                        # General Strike (Un): In each City, shift toward Neutral and place any 1 Guerrilla.
                        cities = [s.id for s in self.board.spaces if s.type == 0]
                        if cities:
                            # Shift all cities first
                            for s_id in cities:
                                s = self.board.spaces[s_id]
                                _shift_alignment(s, toward_neutral=True)
                            # Then choose faction per city
                            self._pending_event_faction = {"event": "GENERAL_STRIKE_UN_FACTION", "allowed": [1, 2, 3], "cities": cities, "city_idx": 0}
                            self.phase = PHASE_CHOOSE_TARGET_FACTION
                        else:
                            player.eligible = False
                            if not self.keep_eligible_this_action:
                                self.ineligible_next_card.add(self.current_player_num)
                            self.card_action_slot += 1
                            self.phase = PHASE_CHOOSE_MAIN
                            self._pending_main = None
                        advance_turn = False
                    else:
                        # General Strike (Sh): Select a City. Set it to Active Support. Activate ALL Guerrillas there. Open 1 Casino.
                        self._pending_event_target = {"event": "GENERAL_STRIKE_SH"}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                elif card_id == 4 and not play_shaded:
                    # S.I.M (Un): Remove Support from a space with no Police.
                    self._pending_event_target = {"event": "SIM_UN"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 7:
                    if not play_shaded:
                        # Election (Un): Place 1 Guerrilla in each City - faction choice per city.
                        cities = [s.id for s in self.board.spaces if s.type == 0]
                        if cities:
                            self._pending_event_faction = {"event": "ELECTION_UN_FACTION", "allowed": [1, 2, 3], "cities": cities, "city_idx": 0}
                            self.phase = PHASE_CHOOSE_TARGET_FACTION
                        else:
                            # No cities (shouldn't happen)
                            player.eligible = False
                            if not self.keep_eligible_this_action:
                                self.ineligible_next_card.add(self.current_player_num)
                            self.card_action_slot += 1
                            self.phase = PHASE_CHOOSE_MAIN
                            self._pending_main = None
                        advance_turn = False
                    else:
                        # Election (Sh): Select a City. Set to Neutral. Aid +10.
                        self._pending_event_target = {"event": "ELECTION_SH"}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                elif card_id == 15 and not play_shaded:
                    # Come Comrades! (Un): Place 3 M26 Guerrillas anywhere.
                    self._pending_event_target = {"event": "COME_COMRADES_UN", "count": 0}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 17 and not play_shaded:
                    # Alberto Bayo (Un): 26July or DR free Rallies in each space it has a Base.
                    # Choose faction.
                    allowed = [1, 2]
                    self._pending_event_faction = {"event": "ALBERTO_BAYO_UN_FACTION", "allowed": allowed}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                elif card_id == 20:
                    if not play_shaded:
                        # The Twelve (Un): A Faction free Marches then free Rallies at a March destination.
                        allowed = [1, 2]
                        self._pending_event_faction = {"event": "THE_TWELVE_UN_FACTION", "allowed": allowed}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                    else:
                        # The Twelve (Sh): Remove 1/2 (rounded up) of any Guerrillas from the space with the most Guerrillas.
                        max_g = 0
                        for sp in self.board.spaces:
                            g = int(sp.pieces[2] + sp.pieces[3] + sp.pieces[5] + sp.pieces[6] + sp.pieces[8] + sp.pieces[9])
                            if g > max_g:
                                max_g = g

                        if max_g <= 0:
                            print(" -> The Twelve (Sh): No Guerrillas on map.")
                        else:
                            self._pending_event_target = {"event": "THE_TWELVE_SH", "max": max_g}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 3 and play_shaded:
                    # Eulogio Cantillo (Sh): Select a Province or City with Troops. They free Sweep in place, then free Assault.
                    self._pending_event_target = {"event": "CANTILLO_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 5 and not play_shaded:
                    # Rolando Masferrer (Un): Set a Province with Troops and 1 adjacent Province to Passive Opposition.
                    self._pending_event_target = {"event": "MASFERRER_UN", "stage": "SPACE1"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 10 and not play_shaded:
                    # MAP (Un): Replace cube with any 2 Guerrillas - choose space first.
                    self._pending_event_target = {"event": "MAP_UN", "count": 0}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 11 and not play_shaded:
                    # Batista Flees (Un): Select and remove a die roll of Troops.
                    self.players[0].resources = max(0, self.players[0].resources - 10)
                    roll = self._roll_die()
                    self._pending_event_target = {"event": "BATISTA_FLEES_UN", "count": roll, "removed": 0}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 16 and play_shaded:
                    # Larrazábal (Sh): Remove one 26July Base.
                    self._pending_event_target = {"event": "LARRAZABAL_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 16 and not play_shaded:
                    # Larrazábal (Un): Place a 26July Base where there is a 26July piece.
                    self._pending_event_target = {"event": "LARRAZABAL_UN"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 21 and not play_shaded:
                    # Fangio (Un): Shift a City 1 level toward Active Opposition (2 if M26 piece).
                    self._pending_event_target = {"event": "FANGIO_UN"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 23:
                    if not play_shaded:
                        # Radio Rebelde (Un): Shift 2 Provinces each 1 level toward Active Opposition.
                        self._pending_event_target = {"event": "RADIO_REBELDE_UN", "count": 0, "picked": []}
                    else:
                        # Radio Rebelde (Sh): Remove a 26July Base from a Province.
                        self._pending_event_target = {"event": "RADIO_REBELDE_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 24:
                    if not play_shaded:
                        # Vilma Espín (Un): Set Sierra Maestra or an adjacent space to Active Opposition.
                        self._pending_event_target = {"event": "VILMA_ESPIN_UN"}
                    else:
                        # Vilma Espín (Sh): Remove all 26July pieces from a City other than Havana.
                        self._pending_event_target = {"event": "VILMA_ESPIN_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 25:
                    if not play_shaded:
                        # Escapade (Un): Place a DR Guerrilla and Base in either Camagüey Province or Oriente.
                        self._pending_event_target = {"event": "ESCAPADE_UN"}
                    else:
                        # Escapade (Sh): Remove a Directorio Base.
                        self._pending_event_target = {"event": "ESCAPADE_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 26:
                    if not play_shaded:
                        # Rodríguez Loeches (Un): DR places 1 Guerrilla anywhere and free Marches to, Rallies, or Ambushes there.
                        self._pending_event_target = {"event": "LOECHES_UN", "stage": "PLACE"}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                    else:
                        # Rodríguez Loeches (Sh): Remove 1 DR Guerrilla. DR Resources –5.
                        self.players[2].resources = max(0, self.players[2].resources - 5)
                        self._pending_event_target = {"event": "LOECHES_SH"}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 27 and not play_shaded:
                    # Echeverría (Un): Place 2 DR Guerrillas anywhere. Havana to Neutral.
                    if self.players[2].available_forces[0] > 0:
                        self._pending_event_target = {"event": "ECHEVERRIA_UN", "count": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                    else:
                        havana = self.board.spaces[3]
                        havana.alignment = 0
                        havana.support_active = False
                        havana.update_control()
                        self.players[2].eligible = True
                        self.ineligible_next_card.discard(2)
                        self.ineligible_through_next_card.discard(2)
                        # Finish action slot (no placements possible).
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                elif card_id == 27 and play_shaded:
                    # Echeverría (Sh): Remove 2 DR pieces closest to Havana. DR Resources –3.
                    self.players[2].resources = max(0, int(self.players[2].resources) - 3)
                    self._pending_event_target = {"event": "ECHEVERRIA_SH", "remaining": 2}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 29:
                    if not play_shaded:
                        # Fauré Chomón (Un): DR or 26July places a Base and 2 Guerrillas in Las Villas.
                        self._pending_event_faction = {"event": "CHOMON_UN_FACTION", "allowed": [1, 2]}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                    else:
                        # Fauré Chomón (Sh): Remove a DR piece or replace it with its 26July counterpart.
                        self._pending_event_target = {"event": "CHOMON_SH"}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 31:
                    if not play_shaded:
                        # Escopeteros (Un): Place any non-Casino Base and any 1 Guerrilla into a Mountain.
                        self._pending_event_target = {"event": "ESCOPETEROS_UN", "stage": "SPACE"}
                    else:
                        # Escopeteros (Sh): Shift a Mountain space 1 level toward Support.
                        self._pending_event_target = {"event": "ESCOPETEROS_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 32:
                    if not play_shaded:
                        # Resistencia Cívica (Un): In a City, replace all Directorio pieces with 26July counterparts.
                        self._pending_event_target = {"event": "RESISTENCIA_UN"}
                    else:
                        # Resistencia Cívica (Sh): In a City, replace all 26July pieces with Directorio counterparts.
                        self._pending_event_target = {"event": "RESISTENCIA_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 35 and not play_shaded:
                    # Defections (Un): In a space already occupied by your pieces and those of an enemy,
                    # replace 2 enemy Guerrillas or cubes with your Guerrillas or cubes.
                    self._pending_event_target = {"event": "DEFECTIONS_UN", "stage": "SPACE"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 30 and play_shaded:
                    # Guerrilla Life (Sh): Flip all DR Guerrillas Underground. Place 1 DR Guerrilla in a City.
                    for sp in self.board.spaces:
                        sp.pieces[5] += sp.pieces[6]
                        if int(sp.cash_holders[6]) > 0:
                            self._move_cash_between_piece_indices(sp, 6, 5, int(sp.cash_holders[6]))
                        sp.pieces[6] = 0
                    self._pending_event_target = {"event": "GUERRILLA_LIFE_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 36:
                    if not play_shaded:
                        # Eloy Gutiérrez Menoyo (Un): Replace a non-DR non-Casino piece within 1 space of Las Villas with 2 DR Guerrillas.
                        self._pending_event_target = {"event": "MENOYO_UN"}
                    else:
                        # Eloy Gutiérrez Menoyo (Sh): Replace a DR Guerrilla with a non-DR Guerrilla.
                        self._pending_event_target = {"event": "MENOYO_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 38:
                    if not play_shaded:
                        # Meyer Lansky (Un): Within a space, transfer any Cash among any Guerrillas or cubes.
                        has_valid_space = any(
                            self._space_total_cash(sp) > 0 and self._space_has_valid_cash_transfer_between_holders(sp)
                            for sp in self.board.spaces
                        )
                        if has_valid_space:
                            self._pending_event_target = {"event": "MEYER_LANSKY_UN", "stage": "SPACE"}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                        else:
                            print(" -> Meyer Lansky (Un): No space has cash to transfer — event fizzles.")
                            player.eligible = False
                            if not self.keep_eligible_this_action:
                                self.ineligible_next_card.add(self.current_player_num)
                            self.card_action_slot += 1
                            self.phase = PHASE_CHOOSE_MAIN
                            self._pending_main = None
                    else:
                        # Meyer Lansky (Sh): Syndicate relocates any Casinos anywhere. All Casinos open.
                        for sp in self.board.spaces:
                            if getattr(sp, "closed_casinos", 0) > 0:
                                sp.pieces[10] += int(sp.closed_casinos)
                                sp.closed_casinos = 0
                                sp.update_control()
                        if self._has_valid_casino_move():
                            self._pending_event_target = {"event": "MEYER_LANSKY_SH", "stage": "SRC"}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                        else:
                            print(" -> Meyer Lansky (Sh): No valid Casino relocations.")
                            player.eligible = False
                            if not self.keep_eligible_this_action:
                                self.ineligible_next_card.add(self.current_player_num)
                            self.card_action_slot += 1
                            self.phase = PHASE_CHOOSE_MAIN
                            self._pending_main = None
                            advance_turn = True
                elif card_id == 19 and not play_shaded:
                    # Manifesto (Un): Each Faction places 2 non-Casino pieces.
                    # In card Faction order. Executing Faction stays Eligible for next card.
                    self.keep_eligible_this_action = True
                    order = list(getattr(self.current_card, "faction_order", [0, 1, 2, 3]))
                    self._pending_event_target = {
                        "event": "MANIFESTO_UN",
                        "order": order,
                        "pos": 0,
                        "f_idx": int(order[0]) if order else 0,
                        "count": 0,
                    }
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 28 and play_shaded:
                    # Morgan (Sh): Set a space with a DR Guerrilla to Active Support.
                    self._pending_event_target = {"event": "MORGAN_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 33 and play_shaded:
                    # Carlos Prío (Sh): Select a space without Govt Control. Place a DR Base there and set to Neutral.
                    self._pending_event_target = {"event": "CARLOS_PRIO_SH"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                elif card_id == 34 and not play_shaded:
                    # US Speaking Tour (Un): An Insurgent Faction adds a die roll in Resources.
                    self._pending_event_faction = {"event": "SPEAKING_TOUR_UN", "allowed": [1, 2]}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                elif card_id == 33 and not play_shaded:
                    # Carlos Prío (Un): +5 DR or +5 M26 Resources.
                    self._pending_event_faction = {"event": "CARLOS_PRIO_UN", "allowed": [1, 2]}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                elif card_id == 47:
                    if not play_shaded:
                        # Pact of Miami (Un): Remove 2 Guerrillas. Govt Ineligible through next card.
                        self.ineligible_through_next_card.add(0) # Govt
                        self._pending_event_target = {"event": "MIAMI_UN", "count": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                    else:
                        # Pact of Miami (Sh): M26 and DR each lose –3 Resources. Both Ineligible.
                        self.players[1].resources = max(0, self.players[1].resources - 3)
                        self.players[2].resources = max(0, self.players[2].resources - 3)
                        self.players[1].eligible = False
                        self.players[2].eligible = False
                        self.ineligible_through_next_card.add(1)
                        self.ineligible_through_next_card.add(2)
                        print(f" -> Pact of Miami (Sh): M26/DR Res -3, Ineligible.")
                        # Finish action
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        advance_turn = False
                else:
                    cost = resolve_event(self, card_id, play_shaded)
                    player.resources = max(0, player.resources - cost)
                    self._last_op_paid_cost = 0

                # If we transitioned into a multi-step event (target selection, option selection, etc.),
                # do not consume the action slot yet.
                if self.phase != PHASE_CHOOSE_EVENT_SIDE:
                    return self.observation, reward, done, False, {}

                # Always ineligible for the remainder of the current card after acting.
                # Some events override next-card eligibility ("Executing Faction stays Eligible").
                player.eligible = False
                if not self.keep_eligible_this_action:
                    self.ineligible_next_card.add(self.current_player_num)
                self.card_action_slot += 1
                self.phase = PHASE_CHOOSE_MAIN
                self._pending_main = None

            # Phase 2: ops action (existing encoding)
            elif self.phase == PHASE_CHOOSE_OP_ACTION:
                ops_action = action - self._ops_action_base
                op = ops_action // self.num_spaces
                s = ops_action % self.num_spaces
                self._last_op = op
                self._last_op_space = s
                self._sa_restrict_op = None
                self._sa_restrict_space = None
                if player.name == "GOVT":
                    if op == OP_TRAIN_FORCE: cost = self._op_train_f_impl(s)
                    elif op == OP_TRAIN_BASE: cost = self._op_train_b_impl(s)
                    elif op == OP_GARRISON:
                        self._pending_op_target = {"op": "GARRISON_SRC", "dest": s, "moved": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_SWEEP:
                        self._pending_event_target = None
                        self._pending_op_target = None
                        self._pending_sa_target = None
                        allow_police = "SIM_Shaded" in self.capabilities
                        self._pending_op_target = {"op": "SWEEP_SRC", "dest": s, "allow_police": allow_police, "moved": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_ASSAULT:
                        if "ArmoredCars_Shaded" in self.capabilities:
                            self._pending_event_target = None
                            self._pending_op_target = None
                            self._pending_sa_target = None
                            self._pending_op_target = {"op": "ASSAULT_REINFORCE_SRC", "dest": s, "limited": False, "context": "OP"}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            cost = 0
                        else:
                            cost = self._op_assault_impl(s, context="OP")
                            if cost is None:
                                self.phase = PHASE_CHOOSE_TARGET_FACTION
                                advance_turn = False
                                cost = 0
                    elif op == OP_TRANSPORT:
                        # Agent selects a source space for Transport.
                        self._pending_event_target = None
                        self._pending_op_target = None
                        self._pending_sa_target = None
                        self._pending_op_target = {"op": "TRANSPORT_SRC", "dest": s}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_AIR_STRIKE: cost = self.op_airstrike(s)
                elif player.name == "M26":
                    if op == OP_RALLY_M26: cost = self.op_rally_m26(s)
                    elif op == OP_MARCH_M26:
                        self._pending_event_target = None
                        self._pending_op_target = None
                        self._pending_sa_target = None
                        self._pending_op_target = {"op": "MARCH_SRC", "dest": s, "u": 2, "a": 3, "moved": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_ATTACK_M26:
                        cost = self._op_attack_insurgent(s, 2, 3, 4)
                        if cost is None:
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            cost = 0
                    elif op == OP_TERROR_M26: cost = self._op_terror_insurgent(s, 2, 3)
                    elif op == OP_AMBUSH_M26:
                        cost = self.op_ambush_m26(s)
                        if cost is None:
                            return self.observation, reward, done, False, {}
                    elif op == OP_KIDNAP_M26:
                        cost = self.op_kidnap_m26(s)
                        if cost is None:
                            return self.observation, reward, done, False, {}
                elif player.name == "DR":
                    if op == OP_RALLY_DR: cost = self.op_rally_dr(s)
                    elif op == OP_MARCH_DR:
                        max_range = 2 if "Morgan_Unshaded" in self.capabilities else 1
                        self._pending_op_target = {"op": "MARCH_SRC", "dest": s, "u": 5, "a": 6, "max_range": max_range, "moved": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_ATTACK_DR:
                        cost = self._op_attack_insurgent(s, 5, 6, 7)
                        if cost is None:
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            cost = 0
                    elif op == OP_TERROR_DR: cost = self._op_terror_insurgent(s, 5, 6)
                    elif op == OP_ASSASSINATE_DR: cost = self.op_assassinate_dr(s)
                elif player.name == "SYNDICATE":
                    if op == OP_RALLY_SYN: cost = self.op_rally_syn(s)
                    elif op == OP_MARCH_SYN:
                        self._pending_op_target = {"op": "MARCH_SRC", "dest": s, "u": 8, "a": 9, "moved": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_ATTACK_SYN:
                        cost = self._op_attack_insurgent(s, 8, 9, 10)
                        if cost is None:
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            cost = 0
                    elif op == OP_TERROR_SYN: cost = self._op_terror_insurgent(s, 8, 9)
                    elif op == OP_BRIBE_SYN: cost = self.op_bribe_syn(s)
                    elif op == OP_CONSTRUCT_SYN: cost = self.op_construct_syn(s)

                player.resources = max(0, player.resources - cost)
                self._last_op_paid_cost = int(cost)

                # If Masferrer shaded is active and we just Swept a space with enemies,
                # offer a free Assault as the special activity in that same space.
                if player.name == "GOVT" and op == OP_SWEEP and "Masferrer_Shaded" in self.capabilities:
                    sp = self.board.spaces[s]
                    if sum(sp.pieces[2:11]) > 0:
                        self._sa_restrict_op = OP_ASSAULT
                        self._sa_restrict_space = s
                        self._sa_free = True

                # After a full Ops, allow an optional Special Activity.
                if self.phase not in [PHASE_CHOOSE_TARGET_SPACE, PHASE_CHOOSE_TARGET_FACTION, PHASE_CHOOSE_EVENT_OPTION]:
                    self._pending_sa = True
                    self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                    advance_turn = False

            elif self.phase == PHASE_CHOOSE_LIMITED_OP_ACTION:
                if self._pending_mafia_offensive is not None:
                    ops_action = action - self._limited_ops_action_base
                    op = ops_action // self.num_spaces
                    s = ops_action % self.num_spaces
                    mafia_faction = int(self._pending_mafia_offensive.get("faction"))

                    if mafia_faction == 1:
                        if op == OP_RALLY_M26:
                            self.op_rally_m26(s)
                        elif op == OP_MARCH_M26:
                            self._pending_op_target = {"op": "MARCH_SRC", "dest": s, "u": 2, "a": 3, "limited": True, "mafia": True, "faction": mafia_faction, "moved": 0, "borrowed_used": False}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                        elif op == OP_ATTACK_M26:
                            self._op_mafia_attack(s, 2, 3)
                        elif op == OP_TERROR_M26:
                            self._op_mafia_terror(s, mafia_faction, 2, 3)
                    elif mafia_faction == 2:
                        if op == OP_RALLY_DR:
                            self.op_rally_dr(s)
                        elif op == OP_MARCH_DR:
                            max_range = 2 if "Morgan_Unshaded" in self.capabilities else 1
                            self._pending_op_target = {"op": "MARCH_SRC", "dest": s, "u": 5, "a": 6, "limited": True, "mafia": True, "faction": mafia_faction, "max_range": max_range, "moved": 0, "borrowed_used": False}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                        elif op == OP_ATTACK_DR:
                            self._op_mafia_attack(s, 5, 6)
                        elif op == OP_TERROR_DR:
                            self._op_mafia_terror(s, mafia_faction, 5, 6)

                    self._pending_mafia_offensive = None
                    self._last_op_paid_cost = 0
                    player.eligible = False
                    self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    advance_turn = True
                    return self.observation, reward, done, False, {}

                ops_action = action - self._limited_ops_action_base
                op = ops_action // self.num_spaces
                s = ops_action % self.num_spaces
                if player.name == "GOVT":
                    if op == OP_TRAIN_FORCE: cost = self._op_train_f_impl(s)
                    elif op == OP_TRAIN_BASE: cost = self._op_train_b_impl(s)
                    elif op == OP_GARRISON:
                        self._pending_op_target = {"op": "GARRISON_SRC", "dest": s, "moved": 0, "limited": True}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_SWEEP:
                        allow_police = "SIM_Shaded" in self.capabilities
                        self._pending_op_target = {"op": "SWEEP_SRC", "dest": s, "allow_police": allow_police, "moved": 0, "limited": True}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_ASSAULT:
                        if "ArmoredCars_Shaded" in self.capabilities:
                            self._pending_op_target = {"op": "ASSAULT_REINFORCE_SRC", "dest": s, "limited": True, "context": "OP"}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            cost = 0
                        else:
                            cost = self._op_assault_impl(s, context="LIMOP")
                            if cost is None:
                                self.phase = PHASE_CHOOSE_TARGET_FACTION
                                advance_turn = False
                                cost = 0
                    elif op == OP_TRANSPORT:
                        self._pending_op_target = {"op": "TRANSPORT_SRC", "dest": s, "limited": True}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                elif player.name == "M26":
                    if op == OP_RALLY_M26: cost = self.op_rally_m26(s)
                    elif op == OP_MARCH_M26:
                        self._pending_op_target = {"op": "MARCH_SRC", "dest": s, "u": 2, "a": 3, "limited": True, "moved": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_ATTACK_M26:
                        cost = self._op_attack_insurgent(s, 2, 3, 4)
                        if cost is None:
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            cost = 0
                    elif op == OP_TERROR_M26: cost = self._op_terror_insurgent(s, 2, 3)
                elif player.name == "DR":
                    if op == OP_RALLY_DR: cost = self.op_rally_dr(s)
                    elif op == OP_MARCH_DR:
                        max_range = 2 if "Morgan_Unshaded" in self.capabilities else 1
                        self._pending_op_target = {"op": "MARCH_SRC", "dest": s, "u": 5, "a": 6, "limited": True, "max_range": max_range, "moved": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_ATTACK_DR:
                        cost = self._op_attack_insurgent(s, 5, 6, 7)
                        if cost is None:
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            cost = 0
                    elif op == OP_TERROR_DR: cost = self._op_terror_insurgent(s, 5, 6)
                elif player.name == "SYNDICATE":
                    if op == OP_RALLY_SYN: cost = self.op_rally_syn(s)
                    elif op == OP_MARCH_SYN:
                        self._pending_op_target = {"op": "MARCH_SRC", "dest": s, "u": 8, "a": 9, "limited": True, "moved": 0}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        cost = 0
                    elif op == OP_ATTACK_SYN:
                        cost = self._op_attack_insurgent(s, 8, 9, 10)
                        if cost is None:
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            cost = 0
                    elif op == OP_TERROR_SYN: cost = self._op_terror_insurgent(s, 8, 9)

                if not self._launder_free:
                    player.resources = max(0, player.resources - cost)
                    self._last_op_paid_cost = int(cost)
                else:
                    self._last_op_paid_cost = 0

                # MAP (shaded): Govt may accompany LimOps with a free Special Activity.
                if self.phase in [PHASE_CHOOSE_TARGET_SPACE, PHASE_CHOOSE_TARGET_FACTION, PHASE_CHOOSE_EVENT_OPTION]:
                    pass
                elif player.name == "GOVT" and "MAP_Shaded" in self.capabilities:
                    self._pending_sa = True
                    self._sa_free = True
                    self._sa_from_limited_ops = True
                    self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                    advance_turn = False
                else:
                    # No Special Activity after this (normal LimOp). Offer Launder if this LimOp was paid for.
                    if self._maybe_start_launder():
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    if self._launder_free:
                        self._launder_free = False
                    player.eligible = False
                    self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None

            elif self.phase == PHASE_CHOOSE_TARGET_SPACE:
                if self._pending_launder is not None and self._pending_launder.get("stage") == "SPACE":
                    s = action - self._target_space_action_base
                    provider = int(self._pending_launder.get("provider"))
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid launder cash space")
                    if s not in self._launder_cash_spaces(provider):
                        raise Exception("Invalid launder cash space")
                    sp = self.board.spaces[int(s)]
                    if not self._remove_cash_marker(sp, provider):
                        raise Exception("Launder: failed to remove cash marker")

                    self._launder_used_this_card = True
                    self._pending_launder = None
                    self._last_op_paid_cost = 0

                    # Execute a free Limited Operation.
                    self._launder_free = True
                    self.current_player_num = int(self._launder_actor)
                    self._launder_actor = None
                    self._pending_main = MAIN_OPS
                    self._begin_pact_action_tracking()
                    self.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
                    advance_turn = False
                    return self.observation, reward, done, False, {}

                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "CIVIC_ACTION":
                    if action == (self._main_action_base + MAIN_PASS):
                        self._propaganda_finish_after_civic_action()
                        return self.observation, float(reward[self.current_player_num]), done, False, {}

                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid civic action target")
                    if s not in self._propaganda_civic_action_targets():
                        raise Exception("Invalid civic action space")

                    sp = self.board.spaces[s]
                    if sp.terror > 0:
                        sp.terror -= 1
                    else:
                        self._shift_toward_active_support(sp)
                    self.players[0].resources = max(0, int(self.players[0].resources) - 4)
                    sp.update_control()

                    if self._propaganda_civic_action_targets():
                        return self.observation, float(reward[self.current_player_num]), done, False, {}

                    self._propaganda_finish_after_civic_action()
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_POLICE_SRC":
                    if action == (self._main_action_base + MAIN_PASS):
                        self._pending_propaganda = {"step": "REDEPLOY_MENU"}
                        self.phase = PHASE_PROPAGANDA_REDEPLOY_MENU
                        return self.observation, float(reward[self.current_player_num]), done, False, {}

                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid police redeploy source")
                    if s not in self._propaganda_redeploy_police_sources():
                        raise Exception("Invalid police redeploy source space")

                    self._pending_propaganda = {"step": "REDEPLOY_POLICE_DEST", "src": s}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_POLICE_DEST":
                    src = int(self._pending_propaganda.get("src"))
                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid police redeploy destination")
                    if s not in self._propaganda_redeploy_police_destinations():
                        raise Exception("Invalid police redeploy destination space")
                    if s == src:
                        raise Exception("Police redeploy destination cannot match source")

                    moved = self._move_pieces_with_cash(src, s, 0, 1, 1)
                    if moved <= 0:
                        raise Exception("No police available to redeploy")

                    self._pending_propaganda = {"step": "REDEPLOY_POLICE_SRC"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_TROOPS_MANDATORY_SRC":
                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid mandatory troop redeploy source")
                    if s not in self._propaganda_redeploy_troop_mandatory_sources():
                        raise Exception("Invalid mandatory troop redeploy source space")

                    self._pending_propaganda = {"step": "REDEPLOY_TROOPS_MANDATORY_DEST", "src": s}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_TROOPS_MANDATORY_DEST":
                    src = int(self._pending_propaganda.get("src"))
                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid mandatory troop redeploy destination")
                    if s not in self._propaganda_redeploy_troop_destinations():
                        raise Exception("Invalid mandatory troop redeploy destination space")
                    if s == src:
                        raise Exception("Troop redeploy destination cannot match source")

                    moved = self._move_pieces_with_cash(src, s, 0, 0, 1)
                    if moved <= 0:
                        print(f"  (no troops to redeploy from {src} to {s} — skipping)")

                    if self._propaganda_redeploy_troop_mandatory_sources():
                        self._pending_propaganda = {"step": "REDEPLOY_TROOPS_MANDATORY_SRC"}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        return self.observation, float(reward[self.current_player_num]), done, False, {}

                    self._pending_propaganda = {"step": "REDEPLOY_MENU"}
                    self.phase = PHASE_PROPAGANDA_REDEPLOY_MENU
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_TROOPS_OPTIONAL_SRC":
                    if action == (self._main_action_base + MAIN_PASS):
                        self._pending_propaganda = {"step": "REDEPLOY_MENU"}
                        self.phase = PHASE_PROPAGANDA_REDEPLOY_MENU
                        return self.observation, float(reward[self.current_player_num]), done, False, {}

                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid optional troop redeploy source")
                    if s not in self._propaganda_redeploy_troop_optional_sources():
                        raise Exception("Invalid optional troop redeploy source space")

                    self._pending_propaganda = {"step": "REDEPLOY_TROOPS_OPTIONAL_DEST", "src": s}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "REDEPLOY_TROOPS_OPTIONAL_DEST":
                    src = int(self._pending_propaganda.get("src"))
                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid optional troop redeploy destination")
                    if s not in self._propaganda_redeploy_troop_destinations():
                        raise Exception("Invalid optional troop redeploy destination space")
                    if s == src:
                        raise Exception("Troop redeploy destination cannot match source")

                    moved = self._move_pieces_with_cash(src, s, 0, 0, 1)
                    if moved <= 0:
                        # Troop disappeared between source and destination selection; loop back
                        print(f"  (Redeploy: no troop left at source, skipping)")

                    self._pending_propaganda = {"step": "REDEPLOY_TROOPS_OPTIONAL_SRC"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "AGITATION":
                    if action == (self._main_action_base + MAIN_PASS):
                        self._propaganda_finish_after_agitation()
                        return self.observation, float(reward[self.current_player_num]), done, False, {}

                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid agitation target")
                    if s not in self._propaganda_agitation_targets():
                        raise Exception("Invalid agitation space")

                    sp = self.board.spaces[s]
                    if sp.terror > 0:
                        sp.terror -= 1
                    else:
                        self._shift_toward_active_opposition(sp)
                    self.players[1].resources = max(0, int(self.players[1].resources) - 1)
                    sp.update_control()

                    if self._propaganda_agitation_targets():
                        return self.observation, float(reward[self.current_player_num]), done, False, {}

                    self._propaganda_finish_after_agitation()
                    return self.observation, float(reward[self.current_player_num]), done, False, {}
                if self._pending_propaganda is not None and self._pending_propaganda.get("step") == "EXPAT_BACKING":
                    if action == (self._main_action_base + MAIN_PASS):
                        self._propaganda_finish_after_expat()
                        return self.observation, float(reward[self.current_player_num]), done, False, {}

                    s = action - self._target_space_action_base
                    if s < 0 or s >= self.num_spaces:
                        raise Exception("Invalid expat backing target")
                    if s not in self._propaganda_expat_targets():
                        raise Exception("Invalid expat backing space")

                    self.op_rally_dr(s)
                    self.board.spaces[s].update_control()
                    self._propaganda_finish_after_expat()
                    return self.observation, float(reward[self.current_player_num]), done, False, {}

                s = action - self._target_space_action_base
                pending = self._pending_event_target
                pending_op = self._pending_op_target
                if pending is None and pending_op is None:
                    raise Exception("Missing pending target in PHASE_CHOOSE_TARGET_SPACE")
                if pending is None and pending_op is not None:
                    op_kind = pending_op.get("op")
                    if op_kind == "TRANSPORT_SRC":
                        dest = pending_op.get("dest")
                        print(f"GOVT: TRANSPORT {self.board.spaces[dest].name}")
                        src = s
                        mx = int(self.board.spaces[src].pieces[0])
                        if mx > 0 and src != dest:
                            mv = min(3, mx)
                            self._move_pieces_with_cash(src, dest, 0, 0, mv)
                        # Transport has no cost in this model.
                        self._pending_op_target = None
                        if pending_op.get("limited") and player.name == "GOVT" and "MAP_Shaded" in self.capabilities:
                            self._pending_sa = True
                            self._sa_free = True
                            self._sa_from_limited_ops = True
                            self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                            advance_turn = False
                        else:
                            # Finish consuming the ops slot.
                            player.eligible = False
                            self.ineligible_next_card.add(self.current_player_num)
                            self.card_action_slot += 1
                            self.phase = PHASE_CHOOSE_MAIN
                            self._pending_main = None
                            advance_turn = True

                            if pending_op.get("limited"):
                                # Limited ops ends immediately (no SA).
                                pass
                            else:
                                # Full ops continues to SA phase.
                                self._pending_sa = True
                                self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                                advance_turn = False
                        return self.observation, reward, done, False, {}

                    if op_kind == "ASSAULT_REINFORCE_SRC":
                        dest = pending_op.get("dest")
                        if dest is None:
                            raise Exception("Assault reinforce: missing destination")

                        if action == (self._main_action_base + MAIN_PASS):
                            # Resolve the Assault after reinforcements.
                            # Resolve the Assault after reinforcements.
                            is_limited = pending_op.get("limited")
                            ctx = "REINFORCE_LIMITED" if is_limited else "REINFORCE_FULL"
                            cost = self._op_assault_impl(int(dest), skip_armored_cars_redeploy=True, context=ctx)
                            if cost is None:
                                self.phase = PHASE_CHOOSE_TARGET_FACTION
                                advance_turn = False
                                cost = 0
                            player.resources = max(0, int(player.resources) - cost)
                            self._pending_op_target = None

                            if pending_op.get("limited") and player.name == "GOVT" and "MAP_Shaded" in self.capabilities:
                                self._pending_sa = True
                                self._sa_free = True
                                self._sa_from_limited_ops = True
                                self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                                advance_turn = False
                                return self.observation, reward, done, False, {}

                            if pending_op.get("limited"):
                                # Finish consuming the limited ops slot.
                                player.eligible = False
                                self.ineligible_next_card.add(self.current_player_num)
                                self.card_action_slot += 1
                                self.phase = PHASE_CHOOSE_MAIN
                                self._pending_main = None
                                advance_turn = True
                                return self.observation, reward, done, False, {}

                            # Full ops continues to SA phase.
                            self._pending_sa = True
                            self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        src = s
                        if int(src) == int(dest):
                            raise Exception("Assault reinforce: source cannot equal destination")
                        if int(self.board.spaces[int(src)].pieces[0]) <= 0:
                            raise Exception("Assault reinforce: no Troops in source")
                        moved = self._move_pieces_with_cash(int(src), int(dest), 0, 0, 1)
                        if moved <= 0:
                            raise Exception("Assault reinforce: failed to move Troops")
                        self._pending_op_target = pending_op
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    if op_kind == "MARCH_SRC":
                        if action == (self._main_action_base + MAIN_PASS):
                            self._finish_march(player, pending_op)
                            return self.observation, reward, done, False, {}

                        dest = pending_op.get("dest")
                        u = pending_op.get("u")
                        a = pending_op.get("a")
                        src = s
                        if src not in self._march_source_ids(pending_op):
                            raise Exception("Invalid March source selection")
                        sp_dest = self.board.spaces[int(dest)]
                        sp_src = self.board.spaces[int(src)]
                        print(f"MARCH {sp_dest.name}")

                        choices = []
                        piece_map = {}
                        opt = 0
                        if sp_src.pieces[u] > 0:
                            piece_map[opt] = int(u)
                            choices.append(opt)
                            opt += 1
                        if sp_src.pieces[a] > 0:
                            piece_map[opt] = int(a)
                            choices.append(opt)
                            opt += 1
                        if pending_op.get("mafia") and sp_src.pieces[8] > 0:
                            if not pending_op.get("borrowed_used"):
                                piece_map[opt] = 8
                                choices.append(opt)
                                opt += 1
                        if pending_op.get("mafia") and sp_src.pieces[9] > 0:
                            if not pending_op.get("borrowed_used"):
                                piece_map[opt] = 9
                                choices.append(opt)
                                opt += 1

                        if not choices:
                            print(" -> No guerrilla to March.")
                            if not self._march_source_ids(pending_op):
                                self._finish_march(player, pending_op)
                                return self.observation, reward, done, False, {}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        if len(choices) > 1:
                            pending_op["src"] = src
                            pending_op["piece_map"] = piece_map
                            self._pending_event_option = {"event": "MARCH_PIECE", "allowed": choices}
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        moved = self._march_move_piece(src, dest, piece_map[choices[0]])
                        if moved:
                            pending_op["moved"] = int(pending_op.get("moved", 0)) + 1
                            if pending_op.get("mafia") and piece_map[choices[0]] in [8, 9]:
                                pending_op["borrowed_used"] = True

                        if not self._march_source_ids(pending_op):
                            self._finish_march(player, pending_op)
                            return self.observation, reward, done, False, {}

                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    if op_kind == "SWEEP_SRC":
                        if action == (self._main_action_base + MAIN_PASS):
                            self._finish_sweep(player, pending_op)
                            return self.observation, reward, done, False, {}

                        dest = pending_op.get("dest")
                        src = s
                        if src not in self._sweep_sources(pending_op):
                            raise Exception("Invalid Sweep source selection")
                        sp_src = self.board.spaces[int(src)]
                        allow_police = bool(pending_op.get("allow_police"))
                        has_troops = int(sp_src.pieces[0]) > 0
                        has_police = int(sp_src.pieces[1]) > 0

                        pending_op["src"] = src
                        if allow_police and has_troops and has_police:
                            self._pending_event_option = {"event": "SWEEP_PIECE", "allowed": [0, 1]}
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        if has_troops:
                            pending_op["piece_type"] = 0
                        elif has_police:
                            pending_op["piece_type"] = 1
                        else:
                            print(" -> No cubes to Sweep from selected source.")
                            if not self._sweep_sources(pending_op):
                                self._finish_sweep(player, pending_op)
                                return self.observation, reward, done, False, {}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        max_count = int(sp_src.pieces[pending_op["piece_type"]])
                        allowed = [0]
                        if max_count >= 2:
                            allowed.append(1)
                        if max_count >= 3:
                            allowed.append(2)
                        self._pending_event_option = {"event": "SWEEP_COUNT", "allowed": allowed}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    if op_kind == "GARRISON_SRC":
                        if action == (self._main_action_base + MAIN_PASS):
                            self._finish_garrison(player, pending_op)
                            return self.observation, reward, done, False, {}

                        src = s
                        if src not in self._garrison_sources(pending_op):
                            raise Exception("Invalid Garrison source selection")
                        sp_src = self.board.spaces[int(src)]
                        if int(sp_src.pieces[1]) <= 0:
                            print(" -> No Police to Garrison from selected source.")
                            if not self._garrison_sources(pending_op):
                                self._finish_garrison(player, pending_op)
                                return self.observation, reward, done, False, {}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        pending_op["src"] = src
                        pending_op["piece_type"] = 1
                        max_count = int(sp_src.pieces[1])
                        allowed = [0]
                        if max_count >= 2:
                            allowed.append(1)
                        if max_count >= 3:
                            allowed.append(2)
                        self._pending_event_option = {"event": "GARRISON_COUNT", "allowed": allowed}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                if pending is None:
                    raise Exception("Missing _pending_event_target in PHASE_CHOOSE_TARGET_SPACE")

                event = pending.get("event")
                if event == "REBEL_AIR_FORCE_UN":
                    faction = pending.get("faction")
                    if faction == "M26":
                        print(f" -> Rebel Air Force (Un): M26 free Ambushes in {self.board.spaces[s].name}.")
                    else:
                        print(f" -> Rebel Air Force (Un): DR free Ambushes in {self.board.spaces[s].name}.")
                    _free_ambush_against_govt_bases_first(self, s)

                elif event == "FAT_BUTCHER_SH":
                    stage = pending.get("stage", "AMBUSH")
                    if stage == "AMBUSH":
                        print(f" -> Fat Butcher (Sh): Free Ambush in {self.board.spaces[s].name}.")
                        _free_ambush_against_govt(self, s)

                        any_closed = any(getattr(sp, "closed_casinos", 0) > 0 for sp in self.board.spaces)
                        if any_closed:
                            pending["stage"] = "OPEN"
                            self._pending_event_target = pending
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        print(" -> Fat Butcher (Sh): No closed Casino to open.")
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        return self.observation, reward, done, False, {}
                    else:
                        sp = self.board.spaces[s]
                        print(f" -> Fat Butcher (Sh): Open Casino in {sp.name}.")
                        if getattr(sp, "closed_casinos", 0) > 0:
                            sp.closed_casinos -= 1
                            sp.pieces[10] += 1
                            sp.update_control()
                        else:
                            print(" -> Fat Butcher (Sh): No closed Casino in selected space.")
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        return self.observation, reward, done, False, {}

                elif event == "FAT_BUTCHER_UN":
                    sp = self.board.spaces[s]
                    print(f" -> Fat Butcher (Un): Close Casino in {sp.name}.")
                    if sp.pieces[10] > 0:
                        self.board.remove_piece(s, 3, 2)
                        sp.closed_casinos += 1
                        sp.update_control()
                    else:
                        print(" -> Fat Butcher (Un): No open Casino in selected space.")
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        return self.observation, reward, done, False, {}

                elif event == "MAP_UN":
                    sp = self.board.spaces[s]
                    print(f" -> MAP (Un): Replace cube in {sp.name} with 2 Guerrillas.")
                    # Remove cube
                    if sp.pieces[1] > 0:
                        sp.pieces[1] -= 1
                        self.players[0].available_forces[1] += 1
                    elif sp.pieces[0] > 0:
                        sp.pieces[0] -= 1
                        self.players[0].available_forces[0] += 1

                    # Transition to faction selection for each guerrilla
                    pending["space"] = s
                    pending["count"] = 0
                    self._pending_event_target = None
                    self._pending_event_faction = {"event": "MAP_UN_FACTION", "allowed": [1, 2, 3], "space": s, "count": 0}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                    return self.observation, reward, done, False, {}

                elif event == "LLANO_SH":
                    sp = self.board.spaces[s]
                    print(f" -> Llano (Sh): Remove Opposition in {sp.name}.")
                    if sp.alignment == 2:
                        sp.alignment = 0
                        sp.support_active = False
                    if self.players[3].available_bases > 0:
                        sp.pieces[10] += 1
                        self.players[3].available_bases -= 1
                        print(f" -> Llano (Sh): Placed open Casino in {sp.name}.")
                    else:
                        print(" -> Llano (Sh): No available Syndicate Casinos.")
                    sp.update_control()
                elif event == "LLANO_UN":
                    sp = self.board.spaces[s]
                    print(f" -> Llano (Un): Place M26 Base in {sp.name}.")
                    # Place M26 Base
                    if self.players[1].available_bases > 0:
                        self.board.add_piece(s, 1, 2)  # M26 Base
                        self.players[1].available_bases -= 1
                    else:
                        print(" -> Llano (Un): No available M26 bases.")

                    # Transition to faction selection for guerrilla
                    self._pending_event_target = None
                    self._pending_event_faction = {"event": "LLANO_UN_FACTION", "allowed": [1, 2, 3], "space": s}
                    self.phase = PHASE_CHOOSE_TARGET_FACTION
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "GENERAL_STRIKE_SH":
                    stage = pending.get("stage", "TARGET")
                    if stage == "TARGET":
                        sp = self.board.spaces[s]
                        print(f" -> General Strike (Sh): {sp.name} set to Active Support.")
                        sp.alignment = 1
                        sp.support_active = True

                        # Activate all Guerrillas (Underground -> Active for all factions).
                        activated = 0
                        for u, a in [(2, 3), (5, 6), (8, 9)]:
                            count = int(sp.pieces[u])
                            if count > 0:
                                sp.pieces[u] -= count
                                sp.pieces[a] += count
                                self._move_cash_between_piece_indices(sp, u, a, count)
                                activated += count
                        print(f" -> Activated {activated} Guerrillas.")
                        sp.update_control()

                        # Open any 1 closed Casino (anywhere).
                        any_closed = any(int(getattr(x, "closed_casinos", 0)) > 0 for x in self.board.spaces)
                        if any_closed:
                            pending["stage"] = "OPEN"
                            pending["city"] = int(s)
                            self._pending_event_target = pending
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                    else:
                        sp = self.board.spaces[s]
                        if int(getattr(sp, "closed_casinos", 0)) > 0:
                            sp.closed_casinos -= 1
                            sp.pieces[10] += 1
                            sp.update_control()
                            print(f" -> General Strike (Sh): Opened Casino in {sp.name}.")
                        else:
                            sp.update_control()
                elif event == "SIM_UN":
                    sp = self.board.spaces[s]
                    print(f" -> S.I.M (Un): Removed Support in {sp.name}.")
                    if sp.alignment == 1:
                        if sp.support_active:
                            sp.support_active = False
                        else:
                            sp.alignment = 0
                    sp.update_control()
                elif event == "ELECTION_SH":
                    sp = self.board.spaces[s]
                    print(f" -> Election (Sh): Set {sp.name} to Neutral.")
                    sp.alignment = 0
                    sp.support_active = False
                    sp.update_control()
                    self.shift_aid(10)
                    print(f" -> Aid +10 (Aid={self.aid}).")
                elif event == "ARMORED_CARS_UN":
                    stage = pending.get("stage", "TARGET")
                    faction = pending.get("faction")
                    if stage == "TARGET":
                        # First selection is the destination. Now request a source space.
                        pending["stage"] = "SRC"
                        pending["dest"] = s
                        self._pending_event_target = pending
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        print(f" -> Armored Cars (Un): Chosen destination {self.board.spaces[s].name}. Now select source.")
                        return self.observation, reward, done, False, {}
                    else:
                        # Stage SRC: Move piece from source to destination, then Ambush.
                        dest_id = pending.get("dest")
                        f_idx = 1 if faction == "M26" else 2
                        u, a = (2, 3) if f_idx == 1 else (5, 6)
                        src_sp = self.board.spaces[s]
                        dest_sp = self.board.spaces[dest_id]

                        print(f" -> Armored Cars (Un): {faction} free March from {src_sp.name} into {dest_sp.name}...")
                        u_count = int(src_sp.pieces[u])
                        a_count = int(src_sp.pieces[a])
                        if u_count > 0:
                            self._move_pieces_with_cash(s, dest_id, f_idx, 0, u_count)
                        if a_count > 0:
                            self._move_pieces_with_cash(s, dest_id, f_idx, 1, a_count)

                        src_sp.update_control()
                        dest_sp.update_control()
                        print(f" -> Armored Cars (Un): Free Ambush in {dest_sp.name}!")
                        _free_ambush_against_govt(self, dest_id)

                elif event == "MOSQUERA_UN":
                    sp = self.board.spaces[s]
                    count = int(sp.pieces[0])
                    sp.pieces[0] = 0
                    self.players[0].available_forces[0] += count
                    print(f" -> Mosquera (Un): Removed {count} Troops from {sp.name}.")

                elif event == "BRAC_UN":
                    count = pending.get("count", 0)
                    sp = self.board.spaces[s]

                    factions_present = []
                    if int(sp.pieces[2] + sp.pieces[3]) > 0:
                        factions_present.append(1)
                    if int(sp.pieces[5] + sp.pieces[6]) > 0:
                        factions_present.append(2)
                    if int(sp.pieces[8] + sp.pieces[9]) > 0:
                        factions_present.append(3)

                    if not factions_present:
                        raise Exception("BRAC (Un): selected space has no guerrillas")

                    if len(factions_present) > 1:
                        self._pending_event_target = {"event": "BRAC_UN", "count": count, "space": s}
                        self._pending_event_faction = {"event": "BRAC_UN_FACTION", "allowed": factions_present, "space": s, "count": count}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    faction = factions_present[0]
                    if faction == 1:
                        u_idx, a_idx = 2, 3
                    elif faction == 2:
                        u_idx, a_idx = 5, 6
                    else:
                        u_idx, a_idx = 8, 9

                    if sp.pieces[u_idx] > 0 and sp.pieces[a_idx] > 0:
                        self._pending_event_target = {"event": "BRAC_UN", "count": count, "space": s, "faction": faction}
                        self._pending_event_option = {
                            "event": "BRAC_UN_PIECE",
                            "allowed": [0, 1],
                            "space": s,
                            "faction": faction,
                            "count": count,
                        }
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    removed = self._brac_remove_guerrilla(sp, faction, prefer_active=False)
                    if removed:
                        count += 1
                        print(f" -> BRAC (Un): Removed guerrilla from {sp.name}.")
                        if count < 2:
                            any_g = any(any(sp.pieces[idx] > 0 for idx in [2,3,5,6,8,9]) for sp in self.board.spaces)
                            if any_g:
                                self._pending_event_target = {"event": "BRAC_UN", "count": count}
                                self.phase = PHASE_CHOOSE_TARGET_SPACE
                                advance_turn = False
                                return self.observation, reward, done, False, {}
                elif event == "BRAC_SH":
                    sp = self.board.spaces[s]
                    add_amt = min(int(self.aid), 6)
                    self.players[0].resources = min(49, int(self.players[0].resources) + add_amt)
                    print(f" -> BRAC (Sh): Govt Resources +{add_amt} (Aid={self.aid}).")
                    if self.players[0].available_forces[1] > 0:
                        self.board.add_piece(s, 0, 1)
                        self.players[0].available_forces[1] -= 1
                        sp.update_control()
                        print(f" -> BRAC (Sh): Placed Police in {sp.name}.")
                    else:
                        print(" -> BRAC (Sh): No Police available.")

                elif event == "COME_COMRADES_UN":
                    count = pending.get("count", 0)
                    sp = self.board.spaces[s]
                    if self.players[1].available_forces[0] > 0:
                        self.board.add_piece(s, 1, 0)
                        self.players[1].available_forces[0] -= 1
                        count += 1
                        print(f" -> Come Comrades! (Un): Placed M26 Guerrilla in {sp.name} (count={count}).")

                    if count < 3 and self.players[1].available_forces[0] > 0:
                        pending["count"] = count
                        self._pending_event_target = pending
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "CARLOS_PRIO_SH":
                    sp = self.board.spaces[s]
                    if self.players[2].available_bases > 0:
                        self.board.add_piece(s, 2, 2) # DR Base
                        self.players[2].available_bases -= 1
                        sp.alignment = 0
                        sp.support_active = False
                        sp.update_control()
                        print(f" -> Carlos Prío (Sh): Placed DR Base in {sp.name} and set to Neutral.")
                    else:
                        print(" -> Carlos Prío (Sh): No available DR bases.")

                elif event == "THE_TWELVE_UN_DEST":
                    faction_name = pending.get("faction")
                    f_idx = 1 if faction_name == "M26" else 2
                    u, a = (2, 3) if f_idx == 1 else (5, 6)

                    dest_id = s
                    dest_sp = self.board.spaces[dest_id]

                    max_range = 1
                    if faction_name == "DR" and "Morgan_Unshaded" in self.capabilities:
                        max_range = 2

                    dist = self._shortest_space_distances(dest_id)
                    moved = 0
                    for src_id, src_sp in enumerate(self.board.spaces):
                        if src_id == dest_id:
                            continue
                        if dist.get(src_id, 999) > max_range:
                            continue
                        if int(src_sp.pieces[u] + src_sp.pieces[a]) <= 0:
                            continue

                        # Move 1 guerrilla (preferring Active) from each eligible source.
                        if int(src_sp.pieces[a]) > 0:
                            self._move_pieces_with_cash(src_id, dest_id, f_idx, 1, 1)
                        else:
                            moved_count = self._move_pieces_with_cash(src_id, dest_id, f_idx, 0, 1)
                            if moved_count > 0 and dest_sp.type in [0, 4]:
                                dest_sp.pieces[u] -= 1
                                dest_sp.pieces[a] += 1
                                self._move_cash_between_piece_indices(dest_sp, u, a, 1)
                        moved += 1

                    dest_sp.update_control()
                    print(f" -> The Twelve (Un): Free March into {dest_sp.name} (moved {moved}).")

                    # Now "Free Rally" at destination (full Rally implementation).
                    print(f" -> The Twelve (Un): Free Rally in {dest_sp.name}")
                    if f_idx == 1:
                        self.op_rally_m26(dest_id)
                    else:
                        self.op_rally_dr(dest_id)

                elif event == "FANGIO_SH":
                    stage = pending.get("stage", "SPACE1")
                    picked = pending.get("picked") or []
                    pending["picked"] = picked
                    pending["space"] = s

                    sp = self.board.spaces[s]
                    allowed = []
                    if getattr(sp, "closed_casinos", 0) > 0:
                        allowed.append(0)  # open closed casino
                    has_piece = (sp.pieces[0] + sp.pieces[1] + sp.pieces[2] + sp.pieces[3] + sp.pieces[5] + sp.pieces[6] + sp.pieces[8] + sp.pieces[9]) > 0
                    if has_piece:
                        allowed.append(1)  # place cash

                    if not allowed:
                        # If no legal sub-option, treat as no-op and continue.
                        print(f" -> Fangio (Sh): No valid option in {sp.name}.")
                        picked.append(s)
                        pending["space"] = None
                        pending["stage"] = "SPACE2" if stage == "SPACE1" else "DONE"
                        if pending["stage"] != "DONE":
                            self._pending_event_target = pending
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                    else:
                        self._pending_event_target = pending
                        self._pending_event_option = {"event": "FANGIO_SH", "allowed": allowed}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "CANTILLO_UN":
                    stage = pending.get("stage", "SPACE")
                    if stage == "SPACE":
                        src_sp = self.board.spaces[s]
                        allowed_factions = []
                        if int(src_sp.pieces[2] + src_sp.pieces[3]) > 0:
                            allowed_factions.append(1)
                        if int(src_sp.pieces[5] + src_sp.pieces[6]) > 0:
                            allowed_factions.append(2)
                        if int(src_sp.pieces[8] + src_sp.pieces[9]) > 0:
                            allowed_factions.append(3)
                        if not allowed_factions:
                            raise Exception("Cantillo (Un): selected space has no guerrillas")
                        pending["src"] = s
                        pending["stage"] = "MOVE"
                        self._pending_event_target = pending
                        self._pending_event_faction = {"event": "CANTILLO_UN_FACTION", "allowed": allowed_factions, "src": s}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    src = pending.get("src")
                    faction = pending.get("faction")
                    if src is None or faction is None:
                        raise Exception("Cantillo (Un): missing src/faction for MOVE stage")

                    if action == (self._main_action_base + MAIN_PASS):
                        src_sp = self.board.spaces[int(src)]
                        if faction == "M26":
                            u, a = 2, 3
                        elif faction == "DR":
                            u, a = 5, 6
                        elif faction == "SYNDICATE":
                            u, a = 8, 9
                        else:
                            raise Exception(f"Cantillo (Un): unknown faction {faction}")

                        if int(src_sp.pieces[u] + src_sp.pieces[a]) > 0:
                            raise Exception("Cantillo (Un): cannot PASS until all Guerrillas have marched out")

                        self._pending_event_target = None
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    dest = s
                    if faction == "M26":
                        u, a = 2, 3
                    elif faction == "DR":
                        u, a = 5, 6
                    elif faction == "SYNDICATE":
                        u, a = 8, 9
                    else:
                        raise Exception(f"Cantillo (Un): unknown faction {faction}")

                    src_sp = self.board.spaces[int(src)]
                    dest_sp = self.board.spaces[int(dest)]

                    f_idx = 1 if faction == "M26" else (2 if faction == "DR" else 3)

                    # Free March out: move 1 Guerrilla (Active preferred), and flip it Underground at destination.
                    if int(src_sp.pieces[a]) > 0:
                        moved = self._move_pieces_with_cash(int(src), int(dest), f_idx, 1, 1)
                        if moved > 0:
                            dest_sp.pieces[a] -= 1
                            dest_sp.pieces[u] += 1
                            self._move_cash_between_piece_indices(dest_sp, a, u, 1)
                    elif int(src_sp.pieces[u]) > 0:
                        self._move_pieces_with_cash(int(src), int(dest), f_idx, 0, 1)
                    else:
                        raise Exception("Cantillo (Un): no Guerrilla remaining to move")

                    print(f" -> Cantillo (Un): {faction} free Marched 1 Guerrilla from {src_sp.name} to {dest_sp.name} (Underground).")

                    src_sp.update_control()
                    dest_sp.update_control()

                    # Continue until all guerrillas are out.
                    pending["stage"] = "MOVE"
                    self._pending_event_target = pending
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                    return self.observation, reward, done, False, {}

                elif event == "CANTILLO_SH":
                    sp = self.board.spaces[s]
                    print(f" -> Cantillo (Sh): Offensive in {sp.name} (Sweep in place then Assault).")
                    cubes = int(sp.pieces[0] + sp.pieces[1])
                    revealed = 0
                    for u, a in [(2,3), (5,6), (8,9)]:
                        h = int(sp.pieces[u])
                        tr = min(h, cubes)
                        sp.pieces[u] -= tr
                        sp.pieces[a] += tr
                        if tr > 0:
                            self._move_cash_between_piece_indices(sp, u, a, tr)
                        revealed += tr
                    print(f"   -> Revealed {revealed} Guerrillas.")
                    print(f"   -> Revealed {revealed} Guerrillas.")
                    cost = self._op_assault_impl(s, context="CANTILLO_SH")

                    if cost is None:
                         # Pause for faction selection
                         self.phase = PHASE_CHOOSE_TARGET_FACTION
                         self._pending_event_target = None # Clear sweep pending stuff? It was None anyway.
                         advance_turn = False
                         return self.observation, reward, done, False, {}

                    # If cost returned, finish immediately.
                    self._pending_event_target = None
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    advance_turn = False # Event always returns advance_turn=False in step?
                    # Wait, if done, we need to advance?
                    # The original code had advance_turn = False.
                    # Because step loop handles advance?
                    # No, return statement exits step.
                    # If advance_turn is False, turn pointer is NOT updated.
                    # So next step call continues in PHASE_CHOOSE_MAIN (new turn)?
                    # No, PHASE_CHOOSE_MAIN usually means "Next Action / Next Card".
                    # If card_action_slot increments, we are moving to next faction.
                    # update_turn_pointer is called at end of step loop if advance_turn=True.
                    # Events usually return False and let next step loop handle it?
                    # Wait, if I return here, I skip update_turn_pointer.
                    # Original code (Lines 3945-3955 in Snippet 763):
                    # returned advance_turn = False.
                    # But it incremented card_action_slot.
                    # So next call to step will see PHASE_CHOOSE_MAIN.
                    # And logic at start of step will pick up next faction.
                    # So correct.
                    return self.observation, reward, done, False, {}

                elif event == "MASFERRER_UN":
                    stage = pending.get("stage", "SPACE1")
                    sp = self.board.spaces[s]
                    sp.alignment = 2 # Opposition
                    sp.support_active = False
                    if stage == "SPACE1":
                        pending["src"] = s
                        pending["stage"] = "SPACE2"
                        print(f" -> Masferrer (Un): Set Province {sp.name} to Opposition.")
                        self._pending_event_target = pending
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    print(f" -> Masferrer (Un): Set adjacent Province {sp.name} to Opposition.")
                    sp.update_control()

                elif event == "BATISTA_FLEES_UN":
                    count = pending.get("count", 0)
                    removed = pending.get("removed", 0)
                    sp = self.board.spaces[s]
                    if sp.pieces[0] > 0:
                        self.board.remove_piece(s, 0, 0)
                        self.players[0].available_forces[0] += 1
                        removed += 1
                        print(f" -> Batista Flees (Un): Removed Troop from {sp.name} ({removed}/{count}).")

                    if removed < count:
                        # Check if any troops left
                        any_troops = any(sp.pieces[0] > 0 for sp in self.board.spaces)
                        if any_troops:
                            pending["removed"] = removed
                            self._pending_event_target = pending
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                    if self.us_alliance < US_ALLIANCE_EMBARGOED:
                        self.shift_us_alliance(1)
                    self.shift_aid(10)
                    self._redeploy_government_deterministic()

                elif event == "LARRAZABAL_SH":
                    sp = self.board.spaces[s]
                    if sp.pieces[4] > 0:
                        self.board.remove_piece(s, 1, 2) # M26 Base
                        self.players[1].available_bases += 1
                        self.players[1].resources = max(0, int(self.players[1].resources) - 3)
                        print(f" -> Larrazábal (Sh): Removed M26 Base from {sp.name}.")
                        sp.update_control()
                elif event == "LARRAZABAL_UN":
                    sp = self.board.spaces[s]
                    print(f" -> Larrazábal (Un): Place M26 Base in {sp.name}.")
                    if self.players[1].available_bases > 0:
                        self.board.add_piece(s, 1, 2)
                        self.players[1].available_bases -= 1
                        sp.update_control()
                    else:
                        print(" -> Larrazábal (Un): No available M26 bases.")

                elif event == "FANGIO_UN":
                    sp = self.board.spaces[s]
                    m26_present = (sp.pieces[2] + sp.pieces[3]) > 0
                    levels = 2 if m26_present else 1
                    # Shift toward Active Opposition (Alignment 2, Support Active False/True)
                    # Simplified shift logic:
                    for _ in range(levels):
                        if sp.alignment == 1: # Support
                            if sp.support_active: sp.support_active = False # Active -> Passive
                            else: sp.alignment = 0 # Passive -> Neutral
                        elif sp.alignment == 0: # Neutral
                            sp.alignment = 2
                            sp.support_active = False # -> Passive Opp
                        elif sp.alignment == 2: # Opposition
                            if not sp.support_active: sp.support_active = True # Passive -> Active
                    sp.update_control()
                    print(f" -> Fangio (Un): Shifted {sp.name} {levels} level(s) toward Active Opposition.")

                elif event == "RADIO_REBELDE_UN":
                    count = pending.get("count", 0)
                    picked = pending.get("picked", [])
                    sp = self.board.spaces[s]
                    # Shift 1 level toward Active Opposition
                    if sp.alignment == 1:
                        if sp.support_active: sp.support_active = False
                        else: sp.alignment = 0
                    elif sp.alignment == 0:
                        sp.alignment = 2
                        sp.support_active = False
                    elif sp.alignment == 2:
                        if not sp.support_active: sp.support_active = True
                    sp.update_control()
                    count += 1
                    picked.append(s)
                    print(f" -> Radio Rebelde (Un): Shifted {sp.name} toward Opposition ({count}/2).")
                    if count < 2:
                        pending["count"] = count
                        pending["picked"] = picked
                        self._pending_event_target = pending
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "RADIO_REBELDE_SH":
                    sp = self.board.spaces[s]
                    if sp.pieces[4] > 0:
                        self.board.remove_piece(s, 1, 2) # M26 Base
                        self.players[1].available_bases += 1
                        print(f" -> Radio Rebelde (Sh): Removed M26 Base from {sp.name}.")
                        sp.update_control()

                elif event == "VILMA_ESPIN_UN":
                    sp = self.board.spaces[s]
                    sp.alignment = 2
                    sp.support_active = True
                    sp.update_control()
                    print(f" -> Vilma Espín (Un): Set {sp.name} to Active Opposition.")

                elif event == "VILMA_ESPIN_SH":
                    sp = self.board.spaces[s]
                    # Remove all 26July pieces
                    for idx in [2, 3, 4]:
                        cnt = sp.pieces[idx]
                        if cnt > 0:
                            sp.pieces[idx] = 0
                            if idx < 4:
                                self.players[1].available_forces[0] += cnt
                            else:
                                self.players[1].available_bases += cnt
                    sp.update_control()
                    print(f" -> Vilma Espín (Sh): Removed all M26 pieces from {sp.name}.")

                elif event == "ESCAPADE_UN":
                    sp = self.board.spaces[s]
                    if self.players[2].available_bases > 0:
                        self.board.add_piece(s, 2, 2) # DR Base
                        self.players[2].available_bases -= 1
                    if self.players[2].available_forces[0] > 0:
                        self.board.add_piece(s, 2, 0) # DR Guerrilla (Underground)
                        self.players[2].available_forces[0] -= 1
                    sp.update_control()
                    print(f" -> Escapade (Un): Placed DR Base and Guerrilla in {sp.name}.")

                elif event == "ESCAPADE_SH":
                    sp = self.board.spaces[s]
                    if sp.pieces[7] > 0:
                        self.board.remove_piece(s, 2, 2) # DR Base
                        self.players[2].available_bases += 1
                        print(f" -> Escapade (Sh): Removed DR Base from {sp.name}.")
                        sp.update_control()

                elif event == "LOECHES_UN":
                    stage = pending.get("stage", "PLACE")
                    sp = self.board.spaces[s]
                    if stage == "PLACE":
                        if self.players[2].available_forces[0] > 0:
                            self.board.add_piece(s, 2, 0) # DR Guerrilla
                            self.players[2].available_forces[0] -= 1
                        sp.update_control()
                        pending["stage"] = "OPTION"
                        pending["place_id"] = s
                        self._pending_event_target = pending
                        # DR free March, Rally, or Ambush there.
                        # For now, let's offer these as options.
                        allowed = [1, 2]
                        has_adj = any(
                            (self.board.spaces[adj_id].pieces[5] + self.board.spaces[adj_id].pieces[6]) > 0
                            for adj_id in sp.adj_ids
                        )
                        if has_adj:
                            allowed.insert(0, 0)
                        self._pending_event_option = {"event": "LOECHES_UN", "allowed": allowed, "space": s}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "LOECHES_SH":
                    sp = self.board.spaces[s]
                    self.board.remove_piece(s, 2, 0) # Underground
                    self.players[2].available_forces[0] += 1
                    sp.update_control()
                    print(f" -> Rodríguez Loeches (Sh): Removed DR Guerrilla from {sp.name}.")
                elif event == "LOECHES_UN_MARCH":
                    dest = pending.get("dest")
                    if dest is None:
                        raise Exception("Rodríguez Loeches (Un): missing destination")
                    src = s
                    src_sp = self.board.spaces[src]
                    dest_sp = self.board.spaces[int(dest)]
                    if src_sp.pieces[6] > 0:
                        self.board.remove_piece(src, 2, 1) # DR Active
                        self.board.add_piece(int(dest), 2, 1)
                    elif src_sp.pieces[5] > 0:
                        self.board.remove_piece(src, 2, 0) # DR Underground
                        act = (dest_sp.type in [0, 4])
                        self.board.add_piece(int(dest), 2, 1 if act else 0)
                    else:
                        print(" -> Rodríguez Loeches (Un): No guerrillas to March.")
                    src_sp.update_control()
                    dest_sp.update_control()
                    print(f" -> Rodríguez Loeches (Un): DR free March into {dest_sp.name}.")

                elif event == "ECHEVERRIA_SH":
                    remaining = int(pending.get("remaining", 0))
                    sp = self.board.spaces[s]
                    opts = []
                    if int(sp.pieces[5]) > 0:
                        opts.append(0)  # Underground
                    if int(sp.pieces[6]) > 0:
                        opts.append(1)  # Active
                    if int(sp.pieces[7]) > 0:
                        opts.append(2)  # Base
                    if not opts:
                        raise Exception("Echeverría (Sh): selected space has no DR pieces")
                    if len(opts) > 1:
                        self._pending_event_target = {"event": "ECHEVERRIA_SH", "remaining": remaining, "space": s}
                        self._pending_event_option = {"event": "ECHEVERRIA_SH_PIECE", "allowed": opts, "space": s, "remaining": remaining}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    opt = opts[0]
                    if opt == 0:
                        self.board.remove_piece(s, 2, 0)
                        self.players[2].available_forces[0] += 1
                    elif opt == 1:
                        self.board.remove_piece(s, 2, 1)
                        self.players[2].available_forces[0] += 1
                    else:
                        self.board.remove_piece(s, 2, 2)
                        self.players[2].available_bases += 1
                    remaining -= 1
                    print(f" -> Echeverría (Sh): Removed DR piece from {sp.name} ({2 - remaining}/2).")
                    sp.update_control()
                    if remaining > 0:
                        self._pending_event_target = {"event": "ECHEVERRIA_SH", "remaining": remaining}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "ECHEVERRIA_UN":
                    count = pending.get("count", 0)
                    sp = self.board.spaces[s]
                    if self.players[2].available_forces[0] > 0:
                        self.board.add_piece(s, 2, 0)
                        self.players[2].available_forces[0] -= 1
                        count += 1
                    print(f" -> Echeverría (Un): Placed DR Guerrilla in {sp.name} ({count}/2).")
                    sp.update_control()
                    if count < 2 and self.players[2].available_forces[0] > 0:
                        pending["count"] = count
                        self._pending_event_target = pending
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    havana = self.board.spaces[3]
                    havana.alignment = 0
                    havana.support_active = False
                    havana.update_control()
                    self.players[2].eligible = True
                    self.ineligible_next_card.discard(2)
                    self.ineligible_through_next_card.discard(2)

                elif event == "CHOMON_SH":
                    sp = self.board.spaces[s]
                    piece_opts = []
                    if int(sp.pieces[5]) > 0:
                        piece_opts.append(0)
                    if int(sp.pieces[6]) > 0:
                        piece_opts.append(1)
                    if int(sp.pieces[7]) > 0:
                        piece_opts.append(2)
                    if not piece_opts:
                        raise Exception("Fauré Chomón (Sh): no DR pieces in selected space")
                    if len(piece_opts) > 1:
                        self._pending_event_target = {"event": "CHOMON_SH", "space": s}
                        self._pending_event_option = {"event": "CHOMON_SH_PIECE", "allowed": piece_opts, "space": s}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    piece_choice = piece_opts[0]
                    can_replace = (
                        self.players[1].available_bases > 0 if piece_choice == 2
                        else self.players[1].available_forces[0] > 0
                    )
                    if can_replace:
                        self._pending_event_target = {"event": "CHOMON_SH", "space": s, "piece": piece_choice}
                        self._pending_event_option = {
                            "event": "CHOMON_SH_ACTION",
                            "allowed": [0, 1],
                            "space": s,
                            "piece": piece_choice,
                        }
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    if piece_choice == 0:
                        self.board.remove_piece(s, 2, 0)
                        self.players[2].available_forces[0] += 1
                    elif piece_choice == 1:
                        self.board.remove_piece(s, 2, 1)
                        self.players[2].available_forces[0] += 1
                    else:
                        self.board.remove_piece(s, 2, 2)
                        self.players[2].available_bases += 1
                    sp.update_control()
                    print(f" -> Fauré Chomón (Sh): Removed DR piece from {sp.name}.")

                elif event == "ESCOPETEROS_UN":
                    # Stage SPACE. Now choose base faction.
                    base_allowed = []
                    if self.players[0].available_bases > 0:
                        base_allowed.append(0)
                    if self.players[1].available_bases > 0:
                        base_allowed.append(1)
                    if self.players[2].available_bases > 0:
                        base_allowed.append(2)
                    if base_allowed:
                        self._pending_event_target = {"event": "ESCOPETEROS_UN", "stage": "BASE", "space": s}
                        self._pending_event_faction = {"event": "ESCOPETEROS_UN_BASE", "allowed": base_allowed, "space": s}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    # No bases available, skip to guerrilla selection.
                    guerrilla_allowed = []
                    if self.players[1].available_forces[0] > 0:
                        guerrilla_allowed.append(1)
                    if self.players[2].available_forces[0] > 0:
                        guerrilla_allowed.append(2)
                    if self.players[3].available_forces[0] > 0:
                        guerrilla_allowed.append(3)
                    if guerrilla_allowed:
                        self._pending_event_target = {"event": "ESCOPETEROS_UN", "stage": "GUERRILLA", "space": s}
                        self._pending_event_faction = {"event": "ESCOPETEROS_UN_GUERRILLA", "allowed": guerrilla_allowed, "space": s}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    # No placements possible.
                    sp = self.board.spaces[s]
                    print(f" -> Escopeteros (Un): No bases or guerrillas available for {sp.name}.")

                elif event == "ESCOPETEROS_SH":
                    sp = self.board.spaces[s]
                    if sp.alignment == 2: # Opp
                        if sp.support_active: sp.support_active = False
                        else: sp.alignment = 0
                    elif sp.alignment == 0:
                        sp.alignment = 1
                        sp.support_active = False
                    elif sp.alignment == 1:
                        if not sp.support_active: sp.support_active = True
                    sp.update_control()
                    print(f" -> Escopeteros (Sh): Shifted {sp.name} toward Support.")

                elif event == "RESISTENCIA_UN":
                    sp = self.board.spaces[s]
                    # Replace all DR with M26
                    replaced = 0
                    for dr_idx, m_idx in [(5,2), (6,3), (7,4)]:
                        cnt = sp.pieces[dr_idx]
                        if cnt > 0:
                            for _ in range(int(cnt)):
                                self.board.remove_piece(s, 2, dr_idx - 5)
                            if dr_idx < 7:
                                self.players[2].available_forces[0] += cnt
                            else:
                                self.players[2].available_bases += cnt
                            # Place as many M26 as available
                            if m_idx < 4:
                                place = min(cnt, self.players[1].available_forces[0])
                                sp.pieces[m_idx] += place
                                self.players[1].available_forces[0] -= int(place)
                            else:
                                place = min(cnt, self.players[1].available_bases)
                                sp.pieces[m_idx] += place
                                self.players[1].available_bases -= int(place)
                            replaced += place
                    sp.update_control()
                    print(f" -> Resistencia Cívica (Un): Replaced DR pieces with {replaced} M26 in {sp.name}.")

                elif event == "RESISTENCIA_SH":
                    sp = self.board.spaces[s]
                    # Replace all M26 with DR
                    replaced = 0
                    for m_idx, dr_idx in [(2,5), (3,6), (4,7)]:
                        cnt = sp.pieces[m_idx]
                        if cnt > 0:
                            for _ in range(int(cnt)):
                                self.board.remove_piece(s, 1, m_idx - 2)
                            if m_idx < 4:
                                self.players[1].available_forces[0] += cnt
                            else:
                                self.players[1].available_bases += cnt

                            if dr_idx < 7:
                                place = min(cnt, self.players[2].available_forces[0])
                                sp.pieces[dr_idx] += place
                                self.players[2].available_forces[0] -= int(place)
                            else:
                                place = min(cnt, self.players[2].available_bases)
                                sp.pieces[dr_idx] += place
                                self.players[2].available_bases -= int(place)
                            replaced += place
                    sp.update_control()
                    print(f" -> Resistencia Cívica (Sh): Replaced M26 pieces with {replaced} DR in {sp.name}.")

                elif event == "DEFECTIONS_UN":
                    sp = self.board.spaces[s]
                    p_idx = self.current_player_num
                    if "enemy_faction" not in pending:
                        enemy_factions = []
                        for f in range(4):
                            if f == p_idx:
                                continue
                            if self._any_piece_present_for_faction(sp, f):
                                enemy_factions.append(f)
                        if not enemy_factions:
                            raise Exception("Defections (Un): no enemy pieces in selected space")
                        if len(enemy_factions) > 1:
                            self._pending_event_target = {"event": "DEFECTIONS_UN", "stage": "SPACE", "space": s}
                            self._pending_event_faction = {"event": "DEFECTIONS_UN_ENEMY", "allowed": enemy_factions, "space": s}
                            self.phase = PHASE_CHOOSE_TARGET_FACTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                        pending["enemy_faction"] = enemy_factions[0]

                    enemy = int(pending.get("enemy_faction"))
                    if enemy == 0:
                        u_idx, a_idx, b_idx = 0, 1, None
                        has_base = False
                    elif enemy == 1:
                        u_idx, a_idx, b_idx = 2, 3, 4
                        has_base = False
                    elif enemy == 2:
                        u_idx, a_idx, b_idx = 5, 6, 7
                        has_base = False
                    else:
                        u_idx, a_idx, b_idx = 8, 9, 10
                        has_base = False

                    piece_opts = []
                    if int(sp.pieces[u_idx]) > 0:
                        piece_opts.append(0)  # Underground
                    if int(sp.pieces[a_idx]) > 0:
                        piece_opts.append(1)  # Active

                    if not piece_opts:
                        # Enemy has only bases (no replaceable guerrillas/cubes) — event ends
                        print(f" -> Defections (Un): enemy has no Guerrillas or cubes to replace.")
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        self._pending_event_target = None
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    if len(piece_opts) == 1:
                        # Important: if Govt is the acting faction and it has both Troops and Police available,
                        # we must not auto-resolve the removal+replacement loop, because the agent needs to
                        # explicitly choose which cube (Troop vs Police) replaces the removed enemy piece.
                        if int(self.current_player_num) == 0 and int(self.players[0].available_forces[0]) > 0 and int(self.players[0].available_forces[1]) > 0:
                            self._pending_event_target = {"event": "DEFECTIONS_UN", "space": s, "enemy_faction": enemy, "remaining": 2}
                            self._pending_event_option = {
                                "event": "DEFECTIONS_UN_PIECE",
                                "allowed": piece_opts,
                                "space": s,
                                "enemy_faction": enemy,
                                "remaining": 2,
                            }
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        remaining = 2
                        opt = piece_opts[0]
                        while remaining > 0:
                            removed = False
                            if opt == 0 and int(sp.pieces[u_idx]) > 0:
                                if enemy == 0:
                                    sp.pieces[u_idx] -= 1
                                else:
                                    self.board.remove_piece(s, enemy, 0)
                                removed = True
                            elif opt == 1 and int(sp.pieces[a_idx]) > 0:
                                if enemy == 0:
                                    sp.pieces[a_idx] -= 1
                                else:
                                    self.board.remove_piece(s, enemy, 1)
                                removed = True
                            if not removed:
                                break

                            if enemy == 0:
                                if opt in [0, 1]:
                                    self.players[0].available_forces[opt] += 1
                                elif opt == 2:
                                    self.players[0].available_bases += 1
                            elif enemy == 1:
                                if opt in [0, 1]:
                                    self.players[1].available_forces[0] += 1
                                elif opt == 2:
                                    self.players[1].available_bases += 1
                            elif enemy == 2:
                                if opt in [0, 1]:
                                    self.players[2].available_forces[0] += 1
                                elif opt == 2:
                                    self.players[2].available_bases += 1
                            else:
                                if opt in [0, 1]:
                                    self.players[3].available_forces[0] += 1
                                elif opt == 2:
                                    self.players[3].available_bases += 1

                            p_idx = self.current_player_num
                            if p_idx == 0:
                                if int(self.players[0].available_forces[0]) > 0 and int(self.players[0].available_forces[1]) > 0:
                                    self._pending_event_target = {
                                        "event": "DEFECTIONS_UN",
                                        "space": s,
                                        "enemy_faction": enemy,
                                        "remaining": remaining,
                                        "stage": "RESUME",
                                    }
                                    self._pending_event_option = {
                                        "event": "DEFECTIONS_UN_GOVT_REPLACE_CUBE",
                                        "allowed": [0, 1],
                                        "space": s,
                                        "enemy_faction": enemy,
                                        "remaining": remaining,
                                    }
                                    self.phase = PHASE_CHOOSE_EVENT_OPTION
                                    advance_turn = False
                                    return self.observation, reward, done, False, {}
                                if int(self.players[0].available_forces[0]) > 0:
                                    self.board.add_piece(int(s), 0, 0)
                                    self.players[0].available_forces[0] -= 1
                                elif int(self.players[0].available_forces[1]) > 0:
                                    self.board.add_piece(int(s), 0, 1)
                                    self.players[0].available_forces[1] -= 1
                            else:
                                if self.players[p_idx].available_forces[0] > 0:
                                    self.board.add_piece(int(s), p_idx, 0)
                                    self.players[p_idx].available_forces[0] -= 1

                            remaining -= 1
                        sp.update_control()
                    else:
                        self._pending_event_target = {"event": "DEFECTIONS_UN", "space": s, "enemy_faction": enemy, "remaining": 2}
                        self._pending_event_option = {
                            "event": "DEFECTIONS_UN_PIECE",
                            "allowed": piece_opts,
                            "space": s,
                            "enemy_faction": enemy,
                            "remaining": 2,
                        }
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "MENOYO_UN":
                    sp = self.board.spaces[s]
                    allowed = []
                    if sp.pieces[0] > 0:
                        allowed.append(0)
                    if sp.pieces[1] > 0:
                        allowed.append(1)
                    if sp.govt_bases > 0:
                        allowed.append(2)
                    if sp.pieces[2] > 0:
                        allowed.append(3)
                    if sp.pieces[3] > 0:
                        allowed.append(4)
                    if sp.pieces[4] > 0:
                        allowed.append(5)
                    if sp.pieces[8] > 0:
                        allowed.append(6)
                    if sp.pieces[9] > 0:
                        allowed.append(7)

                    if not allowed:
                        raise Exception("Eloy Gutiérrez Menoyo (Un): no eligible pieces")
                    if len(allowed) > 1:
                        self._pending_event_target = {"event": "MENOYO_UN", "space": s}
                        self._pending_event_option = {"event": "MENOYO_UN_PIECE", "allowed": allowed, "space": s}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    removed = self._menoyo_un_remove_piece(sp, allowed[0])
                    if removed:
                        for _ in range(2):
                            if self.players[2].available_forces[0] > 0:
                                self.board.add_piece(s, 2, 0)
                                self.players[2].available_forces[0] -= 1
                        sp.update_control()
                        print(f" -> Eloy Gutiérrez Menoyo (Un): Replaced piece with 2 DR in {sp.name}.")

                elif event == "MENOYO_SH":
                    sp = self.board.spaces[s]
                    allowed = []
                    if sp.pieces[5] > 0:
                        allowed.append(0)  # Underground
                    if sp.pieces[6] > 0:
                        allowed.append(1)  # Active
                    if not allowed:
                        raise Exception("Eloy Gutiérrez Menoyo (Sh): no DR guerrillas")
                    if len(allowed) > 1:
                        self._pending_event_target = {"event": "MENOYO_SH", "space": s}
                        self._pending_event_option = {"event": "MENOYO_SH_PIECE", "allowed": allowed, "space": s}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    opt = allowed[0]
                    if opt == 0:
                        self.board.remove_piece(s, 2, 0)
                    else:
                        self.board.remove_piece(s, 2, 1)
                    self.players[2].available_forces[0] += 1

                    allowed_factions = []
                    if self.players[1].available_forces[0] > 0:
                        allowed_factions.append(1)
                    if self.players[3].available_forces[0] > 0:
                        allowed_factions.append(3)

                    if allowed_factions:
                        self._pending_event_faction = {"event": "MENOYO_SH_FACTION", "allowed": allowed_factions, "space": s}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    sp.update_control()
                    print(f" -> Eloy Gutiérrez Menoyo (Sh): Removed DR from {sp.name}.")

                elif event == "MEYER_LANSKY_UN":
                    stage = pending.get("stage", "SPACE")
                    if stage == "SPACE":
                        sp = self.board.spaces[s]
                        if self._space_total_cash(sp) <= 0:
                            print(" -> Meyer Lansky (Un): No cash in selected space.")
                        else:
                            pending["space"] = s
                            pending["stage"] = "SRC_HOLDER"
                            self._pending_event_target = pending
                            self.phase = PHASE_CHOOSE_TARGET_PIECE
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                elif event == "MEYER_LANSKY_SH":
                    stage = pending.get("stage", "SRC")
                    if stage == "SRC":
                        pending["src"] = s
                        pending["stage"] = "DEST"
                        self._pending_event_target = pending
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    src_id = pending.get("src")
                    if src_id is None:
                        raise Exception("Meyer Lansky (Sh): missing source")
                    dest_id = s
                    src_sp = self.board.spaces[int(src_id)]
                    dest_sp = self.board.spaces[int(dest_id)]
                    if src_sp.pieces[10] > 0:
                        self._move_pieces_with_cash(src_id, dest_id, 3, 2, 1)
                        print(f" -> Meyer Lansky (Sh): Moved Casino {src_sp.name} -> {dest_sp.name}.")
                    else:
                        print(" -> Meyer Lansky (Sh): No Casino in selected source.")

                    if self._has_valid_casino_move():
                        self._pending_event_target = {"event": "MEYER_LANSKY_SH", "stage": "SRC"}
                        self._pending_event_option = {"event": "MEYER_LANSKY_SH", "allowed": [0, 1]}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "MORGAN_SH":
                    sp = self.board.spaces[s]
                    print(f" -> Morgan (Sh): Set {sp.name} to Active Support.")
                    sp.alignment = 1
                    sp.support_active = True
                    sp.update_control()

                elif event == "MANIFESTO_UN":
                    f_idx = int(pending.get("f_idx", 0))
                    count = int(pending.get("count", 0))
                    pos = int(pending.get("pos", 0))
                    order = list(pending.get("order", [0, 1, 2, 3]))

                    sp = self.board.spaces[s]
                    faction = self.players[f_idx]

                    # If more than one non-Casino piece type is available, allow explicit choice.
                    allowed = []
                    if f_idx == 0:
                        if int(faction.available_forces[0]) > 0:
                            allowed.append(0)  # Troop
                        if int(faction.available_forces[1]) > 0:
                            allowed.append(1)  # Police
                        if int(faction.available_bases) > 0:
                            allowed.append(2)  # Govt Base
                    elif f_idx in [1, 2]:
                        if int(faction.available_forces[0]) > 0:
                            allowed.append(0)  # Guerrilla
                        if int(faction.available_bases) > 0:
                            allowed.append(1)  # Base
                    else:
                        # Syndicate: Guerrillas only (Casinos excluded).
                        if int(faction.available_forces[0]) > 0:
                            allowed.append(0)

                    if not allowed:
                        print(f"   -> Manifesto (Un): {faction.name} has no available pieces.")
                    elif len(allowed) > 1:
                        self._pending_event_target = {"event": "MANIFESTO_UN", "f_idx": f_idx, "count": count, "pos": pos, "order": order, "space": s}
                        self._pending_event_option = {"event": "MANIFESTO_UN_PIECE", "allowed": allowed, "f_idx": f_idx, "space": s}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    else:
                        opt = allowed[0]
                        if f_idx == 0:
                            if opt == 0 and int(faction.available_forces[0]) > 0:
                                self.board.add_piece(s, 0, 0)
                                faction.available_forces[0] -= 1
                            elif opt == 1 and int(faction.available_forces[1]) > 0:
                                self.board.add_piece(s, 0, 1)
                                faction.available_forces[1] -= 1
                            elif opt == 2 and int(faction.available_bases) > 0:
                                self.board.add_piece(s, 0, 2)
                                faction.available_bases -= 1
                        elif f_idx in [1, 2]:
                            if opt == 0 and int(faction.available_forces[0]) > 0:
                                self.board.add_piece(s, f_idx, 0)
                                faction.available_forces[0] -= 1
                            elif opt == 1 and int(faction.available_bases) > 0:
                                self.board.add_piece(s, f_idx, 2)
                                faction.available_bases -= 1
                        else:
                            if opt == 0 and int(faction.available_forces[0]) > 0:
                                self.board.add_piece(s, 3, 0)
                                faction.available_forces[0] -= 1
                        count += 1
                        print(f"   -> Manifesto (Un): {faction.name} placed piece in {sp.name} ({count}/2).")

                    sp.update_control()

                    if count >= 2:
                        pos += 1
                        count = 0
                        # Advance to next faction in card order that can act.
                        while pos < len(order):
                            cand = int(order[pos])
                            # Must have available non-Casino pieces and at least one space with an existing piece.
                            if cand == 0:
                                has_avail = int(self.players[0].available_forces[0] + self.players[0].available_forces[1] + self.players[0].available_bases) > 0
                                has_space = any(int(sp2.pieces[0] + sp2.pieces[1] + sp2.govt_bases) > 0 for sp2 in self.board.spaces)
                            elif cand == 1:
                                has_avail = int(self.players[1].available_forces[0] + self.players[1].available_bases) > 0
                                has_space = any(int(sp2.pieces[2] + sp2.pieces[3] + sp2.pieces[4]) > 0 for sp2 in self.board.spaces)
                            elif cand == 2:
                                has_avail = int(self.players[2].available_forces[0] + self.players[2].available_bases) > 0
                                has_space = any(int(sp2.pieces[5] + sp2.pieces[6] + sp2.pieces[7]) > 0 for sp2 in self.board.spaces)
                            else:
                                has_avail = int(self.players[3].available_forces[0]) > 0
                                has_space = any(int(sp2.pieces[8] + sp2.pieces[9] + sp2.pieces[10]) > 0 for sp2 in self.board.spaces)
                            if has_avail and has_space:
                                break
                            pos += 1

                    if pos < len(order):
                        pending["pos"] = pos
                        pending["f_idx"] = int(order[pos])
                        pending["count"] = count
                        self._pending_event_target = pending
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    # Finished all factions.
                    self._pending_event_target = None
                    # Finish consuming the event action slot.
                    self.keep_eligible_this_action = True
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    advance_turn = False

                elif event == "THE_TWELVE_SH":
                    sp = self.board.spaces[s]
                    max_g = int(pending.get("max", 0))
                    g_total = int(sp.pieces[2] + sp.pieces[3] + sp.pieces[5] + sp.pieces[6] + sp.pieces[8] + sp.pieces[9])
                    if g_total != max_g:
                        raise Exception("The Twelve (Sh): invalid target (not maximum guerrilla space)")

                    to_remove = (g_total + 1) // 2
                    removed = 0
                    while removed < to_remove:
                        # Deterministic removal order across factions and states.
                        if int(sp.pieces[3]) > 0:
                            self.board.remove_piece(s, 1, 1)
                            self.players[1].available_forces[0] += 1
                        elif int(sp.pieces[2]) > 0:
                            self.board.remove_piece(s, 1, 0)
                            self.players[1].available_forces[0] += 1
                        elif int(sp.pieces[6]) > 0:
                            self.board.remove_piece(s, 2, 1)
                            self.players[2].available_forces[0] += 1
                        elif int(sp.pieces[5]) > 0:
                            self.board.remove_piece(s, 2, 0)
                            self.players[2].available_forces[0] += 1
                        elif int(sp.pieces[9]) > 0:
                            self.board.remove_piece(s, 3, 1)
                            self.players[3].available_forces[0] += 1
                        elif int(sp.pieces[8]) > 0:
                            self.board.remove_piece(s, 3, 0)
                            self.players[3].available_forces[0] += 1
                        else:
                            break
                        removed += 1

                    print(f" -> The Twelve (Sh): Removed {removed}/{to_remove} Guerrillas from {sp.name}.")
                    sp.update_control()

                elif event == "GUERRILLA_LIFE_SH":
                    # Place 1 DR Guerrilla in a City.
                    if self.players[2].available_forces[0] > 0:
                        self.board.add_piece(s, 2, 0)
                        self.players[2].available_forces[0] -= 1
                        print(f" -> The Guerrilla Life (Sh): Placed DR Guerrilla in {self.board.spaces[s].name}.")
                    else:
                        print(" -> The Guerrilla Life (Sh): No available DR Guerrillas.")

                elif event == "CARLOS_PRIO_SH":
                    # Place a DR Base in a space without Govt Control and set to Neutral.
                    sp = self.board.spaces[s]
                    if self.players[2].available_bases > 0:
                        self.board.add_piece(s, 2, 2)
                        self.players[2].available_bases -= 1
                        sp.alignment = 0
                        sp.support_active = False
                        sp.update_control()
                        print(f" -> Carlos Prío (Sh): Placed DR Base in {sp.name}, set to Neutral.")
                    else:
                        print(" -> Carlos Prío (Sh): No available DR bases.")

                elif event == "MIAMI_UN":
                    count = pending.get("count", 0)
                    sp = self.board.spaces[s]
                    # Remove any guerrilla
                    for idx in [2, 3, 5, 6, 8, 9]:
                        if sp.pieces[idx] > 0:
                            f_idx = 1 if idx in [2, 3] else (2 if idx in [5, 6] else 3)
                            self.board.remove_piece(s, f_idx, 0 if idx in [2, 5, 8] else 1)
                            self.players[f_idx].available_forces[0] += 1
                            count += 1
                            break
                    print(f" -> Pact of Miami (Un): Removed guerrilla from {sp.name} ({count}/2).")
                    if count < 2:
                        pending["count"] = count
                        self._pending_event_target = pending
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    sp.update_control()

                else:
                    raise Exception(f"Unhandled pending event target: {event}")

                self._pending_event_target = None

                # Finish consuming the event action slot.
                player.eligible = False
                if not self.keep_eligible_this_action:
                    self.ineligible_next_card.add(self.current_player_num)
                self.card_action_slot += 1
                self.phase = PHASE_CHOOSE_MAIN
                self._pending_main = None

            elif self.phase == PHASE_CHOOSE_TARGET_FACTION:
                if self._pending_launder is not None and self._pending_launder.get("stage") == "PROVIDER":
                    if action == (self._main_action_base + MAIN_PASS):
                        # Decline Launder; finish the original op as normal.
                        self._pending_launder = None
                        self._launder_actor = None
                        self._last_op_paid_cost = 0
                        self._launder_free = False
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        return self.observation, reward, done, False, {}

                    f = action - self._target_faction_action_base
                    if f < 0 or f >= self._target_faction_action_count:
                        raise Exception("Invalid launder provider faction")
                    if f not in self._launder_provider_factions():
                        raise Exception("Invalid launder provider faction")
                    self._pending_launder["provider"] = int(f)
                    self._pending_launder["stage"] = "SPACE"
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                    return self.observation, reward, done, False, {}

                f = action - self._target_faction_action_base
                pending = self._pending_event_faction
                if pending is None:
                    raise Exception("Missing _pending_event_faction in PHASE_CHOOSE_TARGET_FACTION")

                event = pending.get("event")
                allowed = pending.get("allowed") or []
                if f not in allowed:
                    raise Exception("Selected disallowed faction in PHASE_CHOOSE_TARGET_FACTION")

                if event == "OP_ATTACK":
                    s = int(pending["space"])
                    u = int(pending["u"])
                    a = int(pending["a"])
                    b = int(pending["b"])
                    removals = int(pending["removals_left"])

                    cost = self._op_attack_insurgent(s, u, a, b, target_type=None, removals_left=removals, skip_roll=True, target_faction=f)

                    if cost is None:
                        return self.observation, reward, done, False, {}

                    self._pending_event_faction = None
                    if not self._launder_free:
                        player.resources = max(0, player.resources - cost)
                        self._last_op_paid_cost = int(cost)
                    else:
                        self._last_op_paid_cost = 0

                    if self.phase not in [5, 6, 7]:
                         self._pending_sa = True
                         self.phase = 4 # PHASE_CHOOSE_SPECIAL_ACTIVITY
                         advance_turn = False
                    return self.observation, reward, done, False, {}

                if event == "OP_KIDNAP":
                    s = pending["space"]
                    cost = self.op_kidnap_m26(s, target_faction=f)
                    self._pending_event_faction = None
                    if not self._sa_free:
                         player.resources = max(0, player.resources - cost)
                    self._last_op_paid_cost = int(cost)

                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = 0 # PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    self._pending_sa = None
                    self._sa_free = False
                    self._sa_from_limited_ops = False
                    self._sa_restrict_op = None
                    self._sa_restrict_space = None
                    return self.observation, reward, done, False, {}

                if event == "REBEL_AIR_FORCE_SH":
                    # Transfer 1 die roll resources from selected rebel faction to Syndicate.
                    die = int(self._roll_die())
                    amt = min(die, int(self.players[f].resources))
                    self.players[f].resources = int(self.players[f].resources) - amt
                    self.players[3].resources = min(49, int(self.players[3].resources) + amt)
                    print(f" -> Rebel Air Force (Sh): Transferred {amt} (die={die}) from {self.players[f].name} to SYNDICATE.")
                elif event == "OP_ASSAULT":
                    s = pending.get("space")
                    context = pending.get("context")
                    # Execute with selected faction
                    cost = self._op_assault_impl(s, target_faction=f, context=context)

                    player = self.players[self.current_player_num]
                    if not self._sa_free:
                         player.resources = max(0, player.resources - cost)
                    self._last_op_paid_cost = int(cost)

                    self._pending_event_faction = None

                    # Determine Next Phase based on Context
                    if context == "OP" or context == "REINFORCE_FULL":
                         self._pending_sa = True
                         self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                         advance_turn = False
                         return self.observation, reward, done, False, {}

                    elif context == "LIMOP" or context == "REINFORCE_LIMITED" or context == "CANTILLO_SH" or context == "SA":
                         # Check MAP Shaded (Govt LimOp -> SA)
                         if player.name == "GOVT" and "MAP_Shaded" in self.capabilities and context != "CANTILLO_SH":
                              self._pending_sa = True
                              self._sa_free = True
                              self._sa_from_limited_ops = True
                              self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                              advance_turn = False
                              return self.observation, reward, done, False, {}
                         else:
                              # End Turn
                              player.eligible = False
                              if not self.keep_eligible_this_action:
                                  self.ineligible_next_card.add(self.current_player_num)
                              self.card_action_slot += 1
                              self.phase = PHASE_CHOOSE_MAIN
                              self._pending_main = None
                              # Manually advance turn pointer if not done
                              if not done and not self._cash_transfer_waiting:
                                   self.update_turn_pointer()
                              return self.observation, reward, done, False, {}


                elif event == "REBEL_AIR_FORCE_UN_FACTION":
                    # f is selected rebel faction (1=M26, 2=DR)
                    faction_name = "M26" if f == 1 else "DR"
                    self._pending_event_target = {"event": "REBEL_AIR_FORCE_UN", "faction": faction_name}
                    self._pending_event_faction = None
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "MAFIA_OFFENSIVE_UN_FACTION":
                    # Execute a free LimOp for the chosen faction, treating 1 Syndicate piece as theirs.
                    self._pending_mafia_offensive = {"faction": int(f)}
                    self._pending_event_faction = None
                    self.phase = PHASE_CHOOSE_LIMITED_OP_ACTION
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "ALBERTO_BAYO_UN_FACTION":
                    # f is the selected faction (1=M26, 2=DR)
                    print(f" -> Alberto Bayo (Un): {self.players[f].name} Free Rallies in each space with a Base (as if Neutral).")
                    base_idx = 4 if f == 1 else 7
                    for s_id, sp in enumerate(self.board.spaces):
                        if sp.pieces[base_idx] <= 0:
                            continue
                        if f == 1:
                            self.op_rally_m26(s_id)
                            if int(sp.pieces[3]) > 0:
                                moved = int(sp.pieces[3])
                                sp.pieces[3] = 0
                                sp.pieces[2] += moved
                                self._move_cash_between_piece_indices(sp, 3, 2, moved)
                        else:
                            self.op_rally_dr(s_id)
                            if int(sp.pieces[6]) > 0:
                                moved = int(sp.pieces[6])
                                sp.pieces[6] = 0
                                sp.pieces[5] += moved
                                self._move_cash_between_piece_indices(sp, 6, 5, moved)
                        sp.update_control()

                elif event == "THE_TWELVE_UN_FACTION":
                    # f is the selected faction (1=M26, 2=DR)
                    self._pending_event_target = {"event": "THE_TWELVE_UN_DEST", "faction": "M26" if f == 1 else "DR", "stage": "DEST"}
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    self._pending_event_faction = None
                    advance_turn = False
                    return self.observation, reward, done, False, {}

                elif event == "ARMORED_CARS_UN_FACTION":
                    # f is selected faction index (1=M26, 2=DR)
                    self._pending_event_target = {
                        "event": "ARMORED_CARS_UN",
                        "faction": "M26" if f == 1 else "DR",
                    }
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    self._pending_event_faction = None
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "FANGIO_SH_CASH_OWNER":
                    space_id = pending.get("space")
                    if space_id is None:
                        raise Exception("Missing space for FANGIO_SH_CASH_OWNER")
                    sp = self.board.spaces[int(space_id)]
                    # Cash must be placed with a cube/guerrilla belonging to the chosen faction.
                    if int(f) == 0:
                        has_owner_piece = int(sp.pieces[0] + sp.pieces[1]) > 0
                    elif int(f) == 1:
                        has_owner_piece = int(sp.pieces[2] + sp.pieces[3]) > 0
                    elif int(f) == 2:
                        has_owner_piece = int(sp.pieces[5] + sp.pieces[6]) > 0
                    else:
                        has_owner_piece = int(sp.pieces[8] + sp.pieces[9]) > 0
                    if not has_owner_piece:
                        raise Exception("Fangio (Sh): selected cash owner has no cube/guerrilla in space")
                    if not self._add_cash_marker(sp, int(f)):
                        raise Exception("Fangio (Sh): unable to place cash without holder")

                    # Continue Fangio multi-space sequence.
                    if self._pending_event_target is None:
                        raise Exception("Missing _pending_event_target for Fangio continuation")
                    st = self._pending_event_target.get("stage", "SPACE1")
                    picked = self._pending_event_target.get("picked") or []
                    picked.append(int(space_id))
                    self._pending_event_target["picked"] = picked
                    self._pending_event_target["space"] = None
                    self._pending_event_target["stage"] = "SPACE2" if st == "SPACE1" else "DONE"

                    self._pending_event_faction = None

                    if self._pending_event_target["stage"] != "DONE":
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    self._pending_event_target = None
                    # Finish consuming the event action slot.
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                elif event == "CANTILLO_UN_FACTION":
                    src = pending.get("src")
                    if src is None:
                        raise Exception("Cantillo (Un): missing src")
                    if f == 1:
                        faction_name = "M26"
                    elif f == 2:
                        faction_name = "DR"
                    elif f == 3:
                        faction_name = "SYNDICATE"
                    else:
                        raise Exception("Cantillo (Un): invalid faction")

                    self._pending_event_target = {
                        "event": "CANTILLO_UN",
                        "stage": "MOVE",
                        "src": src,
                        "faction": faction_name,
                    }
                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                    self._pending_event_faction = None
                    return self.observation, reward, done, False, {}
                elif event == "CARLOS_PRIO_UN":
                    # Carlos Prío (Un): +5 Resources to M26 or DR.
                    self.players[f].resources = min(49, int(self.players[f].resources) + 5)
                    print(f" -> Carlos Prío (Un): {self.players[f].name} +5 Resources.")

                elif event == "SPEAKING_TOUR_UN":
                    # US Speaking Tour (Un): +die roll for chosen faction, +2 for other.
                    roll = self._roll_die()
                    self.players[f].resources = min(49, int(self.players[f].resources) + roll)
                    print(f" -> US Speaking Tour (Un): {self.players[f].name} +{roll} Res.")
                    # Give +2 to the other insurgent faction
                    other = 2 if f == 1 else 1
                    self.players[other].resources = min(49, int(self.players[other].resources) + 2)
                    print(f" -> {self.players[other].name} +2 Res.")

                elif event == "ELECTION_UN_FACTION":
                    # Election (Un): Place 1 Guerrilla of chosen faction in each City.
                    cities = pending.get("cities", [])
                    city_idx = pending.get("city_idx", 0)

                    if city_idx < len(cities):
                        s_id = cities[city_idx]
                        sp = self.board.spaces[s_id]

                        # Place guerrilla of chosen faction
                        if self.players[f].available_forces[0] > 0:
                            self.board.add_piece(s_id, f, 0)
                            self.players[f].available_forces[0] -= 1
                            print(f" -> Election (Un): Placed {self.players[f].name} in {sp.name}.")
                        else:
                            print(f" -> Election (Un): No available {self.players[f].name} guerrillas.")

                        # Move to next city
                        city_idx += 1
                        if city_idx < len(cities):
                            pending["city_idx"] = city_idx
                            self._pending_event_faction = pending
                            self.phase = PHASE_CHOOSE_TARGET_FACTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                elif event == "GENERAL_STRIKE_UN_FACTION":
                    # General Strike (Un): Place 1 Guerrilla of chosen faction in each City (alignment already shifted).
                    cities = pending.get("cities", [])
                    city_idx = pending.get("city_idx", 0)

                    if city_idx < len(cities):
                        s_id = cities[city_idx]
                        sp = self.board.spaces[s_id]

                        # Place guerrilla of chosen faction
                        if self.players[f].available_forces[0] > 0:
                            self.board.add_piece(s_id, f, 0)
                            self.players[f].available_forces[0] -= 1
                            print(f" -> General Strike (Un): Placed {self.players[f].name} in {sp.name}.")
                        else:
                            print(f" -> General Strike (Un): No available {self.players[f].name} guerrillas.")

                        # Move to next city
                        city_idx += 1
                        if city_idx < len(cities):
                            pending["city_idx"] = city_idx
                            self._pending_event_faction = pending
                            self.phase = PHASE_CHOOSE_TARGET_FACTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                elif event == "MAP_UN_FACTION":
                    # MAP (Un): Place 2 Guerrillas - one at a time with faction choice per guerrilla.
                    s_id = pending.get("space")
                    count = pending.get("count", 0)

                    # Place guerrilla of chosen faction
                    if self.players[f].available_forces[0] > 0:
                        self.board.add_piece(s_id, f, 0)
                        self.players[f].available_forces[0] -= 1
                        print(f" -> MAP (Un): Placed {self.players[f].name} guerrilla ({count+1}/2).")
                    else:
                        print(f" -> MAP (Un): No available {self.players[f].name} guerrillas.")

                    count += 1
                    if count < 2:
                        # Need another guerrilla
                        pending["count"] = count
                        self._pending_event_faction = pending
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "LLANO_UN_FACTION":
                    # Llano (Un): Place any Guerrilla (Base already placed).
                    s_id = pending.get("space")
                    sp = self.board.spaces[s_id]

                    if self.players[f].available_forces[0] > 0:
                        self.board.add_piece(s_id, f, 0)
                        self.players[f].available_forces[0] -= 1
                        print(f" -> Llano (Un): Placed {self.players[f].name} guerrilla in {sp.name}.")
                    else:
                        print(f" -> Llano (Un): No available {self.players[f].name} guerrillas.")
                    sp.update_control()

                elif event == "CHOMON_UN_FACTION":
                    # Faction f chooses to place Base + 2 G in Las Villas (5)
                    sp = self.board.spaces[5]
                    if self.players[f].available_bases > 0:
                        self.board.add_piece(5, f, 2)
                        self.players[f].available_bases -= 1
                    for _ in range(2):
                        if self.players[f].available_forces[0] > 0:
                            self.board.add_piece(5, f, 0)
                            self.players[f].available_forces[0] -= 1
                    sp.update_control()
                    f_name = ["GOVT", "M26", "DR", "SYNDICATE"][f]
                    print(f" -> Fauré Chomón (Un): {f_name} placed Base and 2 Guerrillas in Las Villas.")
                elif event == "ESCOPETEROS_UN_BASE":
                    # Choose a non-casino base faction (Govt/M26/DR), then choose a Guerrilla faction.
                    s_id = pending.get("space")
                    if s_id is None:
                        raise Exception("Escopeteros (Un): missing space for base selection")
                    sp = self.board.spaces[int(s_id)]
                    if int(f) == 0:
                        if self.players[0].available_bases > 0:
                            sp.govt_bases += 1
                            self.players[0].available_bases -= 1
                    elif int(f) in [1, 2]:
                        if self.players[int(f)].available_bases > 0:
                            self.board.add_piece(int(s_id), int(f), 2)
                            self.players[int(f)].available_bases -= 1
                    sp.update_control()
                    base_name = ["GOVT", "M26", "DR", "SYNDICATE"][int(f)]
                    print(f" -> Escopeteros (Un): {base_name} placed Base in {sp.name}.")

                    guerrilla_allowed = []
                    if self.players[1].available_forces[0] > 0:
                        guerrilla_allowed.append(1)
                    if self.players[2].available_forces[0] > 0:
                        guerrilla_allowed.append(2)
                    if self.players[3].available_forces[0] > 0:
                        guerrilla_allowed.append(3)
                    if guerrilla_allowed:
                        self._pending_event_target = {"event": "ESCOPETEROS_UN", "stage": "GUERRILLA", "space": s_id}
                        self._pending_event_faction = {"event": "ESCOPETEROS_UN_GUERRILLA", "allowed": guerrilla_allowed, "space": s_id}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    print(f" -> Escopeteros (Un): No guerrillas available for {sp.name}.")

                elif event == "ESCOPETEROS_UN_GUERRILLA":
                    s_id = pending.get("space")
                    if s_id is None:
                        raise Exception("Escopeteros (Un): missing space for guerrilla selection")
                    sp = self.board.spaces[int(s_id)]
                    if self.players[int(f)].available_forces[0] > 0:
                        self.board.add_piece(int(s_id), int(f), 0)
                        self.players[int(f)].available_forces[0] -= 1
                    sp.update_control()
                    g_name = ["GOVT", "M26", "DR", "SYNDICATE"][int(f)]
                    print(f" -> Escopeteros (Un): {g_name} placed Guerrilla in {sp.name}.")
                elif event == "BRAC_UN_FACTION":
                    space_id = pending.get("space")
                    count = pending.get("count", 0)
                    if space_id is None:
                        raise Exception("BRAC (Un): missing space for faction selection")
                    sp = self.board.spaces[int(space_id)]
                    if f == 1:
                        u_idx, a_idx = 2, 3
                    elif f == 2:
                        u_idx, a_idx = 5, 6
                    else:
                        u_idx, a_idx = 8, 9
                    if sp.pieces[u_idx] > 0 and sp.pieces[a_idx] > 0:
                        self._pending_event_target = {"event": "BRAC_UN", "count": count, "space": space_id, "faction": f}
                        self._pending_event_option = {
                            "event": "BRAC_UN_PIECE",
                            "allowed": [0, 1],
                            "space": space_id,
                            "faction": f,
                            "count": count,
                        }
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    removed = self._brac_remove_guerrilla(sp, f, prefer_active=False)
                    if removed:
                        count += 1
                        print(f" -> BRAC (Un): Removed guerrilla from {sp.name}.")
                        if count < 2:
                            any_g = any(any(sp.pieces[idx] > 0 for idx in [2,3,5,6,8,9]) for sp in self.board.spaces)
                            if any_g:
                                self._pending_event_target = {"event": "BRAC_UN", "count": count}
                                self.phase = PHASE_CHOOSE_TARGET_SPACE
                                advance_turn = False
                                return self.observation, reward, done, False, {}

                elif event == "DEFECTIONS_UN_ENEMY":
                    space_id = pending.get("space")
                    if space_id is None:
                        raise Exception("Defections (Un): missing space for enemy selection")
                    sp = self.board.spaces[int(space_id)]
                    enemy = int(f)
                    if enemy == 0:
                        u_idx, a_idx, b_idx = 0, 1, None
                        has_base = False
                    elif enemy == 1:
                        u_idx, a_idx, b_idx = 2, 3, 4
                        has_base = False
                    elif enemy == 2:
                        u_idx, a_idx, b_idx = 5, 6, 7
                        has_base = False
                    else:
                        u_idx, a_idx, b_idx = 8, 9, 10
                        has_base = False

                    piece_opts = []
                    if int(sp.pieces[u_idx]) > 0:
                        piece_opts.append(0)
                    if int(sp.pieces[a_idx]) > 0:
                        piece_opts.append(1)
                    if not piece_opts:
                        # Enemy has only bases — event ends gracefully
                        print(f" -> Defections (Un): enemy has no Guerrillas or cubes to replace.")
                        player = self.players[self.current_player_num]
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        self._pending_event_target = None
                        self._pending_event_faction = None
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    self._pending_event_target = {"event": "DEFECTIONS_UN", "space": space_id, "enemy_faction": enemy, "remaining": 2}
                    self._pending_event_option = {
                        "event": "DEFECTIONS_UN_PIECE",
                        "allowed": piece_opts,
                        "space": space_id,
                        "enemy_faction": enemy,
                        "remaining": 2,
                    }
                    self.phase = PHASE_CHOOSE_EVENT_OPTION
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "MENOYO_SH_FACTION":
                    space_id = pending.get("space")
                    if space_id is None:
                        raise Exception("Eloy Gutiérrez Menoyo (Sh): missing space for faction choice")
                    sp = self.board.spaces[int(space_id)]
                    if int(f) == 1 and self.players[1].available_forces[0] > 0:
                        self.board.add_piece(int(space_id), 1, 0)
                        self.players[1].available_forces[0] -= 1
                        print(f" -> Eloy Gutiérrez Menoyo (Sh): Replaced DR with M26 in {sp.name}.")
                    elif int(f) == 3 and self.players[3].available_forces[0] > 0:
                        self.board.add_piece(int(space_id), 3, 0)
                        self.players[3].available_forces[0] -= 1
                        print(f" -> Eloy Gutiérrez Menoyo (Sh): Replaced DR with Syndicate in {sp.name}.")
                    else:
                        print(f" -> Eloy Gutiérrez Menoyo (Sh): No available replacement in {sp.name}.")
                    sp.update_control()
                elif event == "MEYER_LANSKY_UN_SRC":
                    space_id = pending.get("space")
                    if space_id is None:
                        raise Exception("Meyer Lansky (Un): missing space for source selection")
                    sp = self.board.spaces[int(space_id)]
                    if self._space_cash_by_faction(sp, int(f)) <= 0:
                        raise Exception("Meyer Lansky (Un): selected source has no cash")
                    if not self._space_has_faction_pieces(sp, int(f)):
                        raise Exception("Meyer Lansky (Un): selected source has no pieces")
                    allowed = [idx for idx in range(4) if self._space_has_faction_pieces(sp, idx)]
                    if not allowed:
                        print(" -> Meyer Lansky (Un): No valid destination factions in space.")
                    else:
                        self._pending_event_faction = {"event": "MEYER_LANSKY_UN_DEST", "allowed": allowed, "space": space_id, "src": f}
                        self._pending_event_target = {"event": "MEYER_LANSKY_UN", "space": space_id}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                elif event == "MEYER_LANSKY_UN_DEST":
                    space_id = pending.get("space")
                    src = pending.get("src")
                    if space_id is None or src is None:
                        raise Exception("Meyer Lansky (Un): missing space/src for destination")
                    sp = self.board.spaces[int(space_id)]
                    if self._space_cash_by_faction(sp, int(src)) <= 0:
                        print(" -> Meyer Lansky (Un): No cash left for source.")
                    else:
                        if not self._space_has_faction_pieces(sp, int(f)):
                            raise Exception("Meyer Lansky (Un): destination has no pieces")
                        self._transfer_cash_marker(sp, int(src), int(f))
                        print(f" -> Meyer Lansky (Un): Moved Cash {self.players[int(src)].name} -> {self.players[int(f)].name} in {sp.name}.")

                    if self._space_has_valid_cash_transfer(sp):
                        self._pending_event_option = {"event": "MEYER_LANSKY_UN", "allowed": [0, 1], "space": space_id}
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                else:
                    raise Exception(f"Unhandled pending faction event: {event}")

                self._pending_event_faction = None

                # Finish consuming the event action slot.
                player.eligible = False
                if not self.keep_eligible_this_action:
                    self.ineligible_next_card.add(self.current_player_num)
                self.card_action_slot += 1
                self.phase = PHASE_CHOOSE_MAIN
                self._pending_main = None

            elif self.phase == PHASE_CHOOSE_EVENT_OPTION:
                opt = action - self._event_option_action_base
                pending = self._pending_event_option
                if pending is None:
                    raise Exception("Missing _pending_event_option in PHASE_CHOOSE_EVENT_OPTION")

                event = pending.get("event")
                allowed = pending.get("allowed") or []
                if opt not in allowed:
                    raise Exception("Selected disallowed option in PHASE_CHOOSE_EVENT_OPTION")

                if event == "OP_ATTACK":
                    # Resume Attack with selected target_type
                    # opt: 0=Troops, 1=Police, 2=Base
                    s = int(pending["space"])
                    u = int(pending["u"])
                    a = int(pending["a"])
                    b = int(pending["b"])
                    removals = int(pending["removals_left"])
                    target_faction = int(pending["target_faction"])

                    cost = self._op_attack_insurgent(s, u, a, b, target_type=opt, removals_left=removals, skip_roll=True, target_faction=target_faction)

                    if cost is None:
                        # Still paused (e.g. 2nd removal needs selection)
                        # Phase remains PHASE_CHOOSE_EVENT_OPTION
                        # _pending_event_option updated by _op_attack_insurgent
                        return self.observation, reward, done, False, {}

                    # Finished
                    self._pending_event_option = None
                    if not self._launder_free:
                        player.resources = max(0, player.resources - cost)
                        self._last_op_paid_cost = int(cost)
                    else:
                        self._last_op_paid_cost = 0

                    if self.phase not in [PHASE_CHOOSE_TARGET_SPACE, PHASE_CHOOSE_TARGET_FACTION]:
                         self._pending_sa = True
                         self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                         advance_turn = False
                    return self.observation, reward, done, False, {}

                if event == "FAT_BUTCHER_UN":
                    # 0 = Close Casino (then choose space), 1 = Aid -8 (immediate)
                    if opt == 0:
                        self._pending_event_option = None
                        self._pending_event_target = {"event": "FAT_BUTCHER_UN"}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    else:
                        self._pending_event_option = None
                        self.shift_aid(-8)
                        print(f" -> Fat Butcher (Un): Aid -8 (Aid={self.aid}).")
                        # Finish action
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        return self.observation, reward, done, False, {}

                elif event == "FANGIO_SH":
                    # 0 = Open Casino, 1 = Cash deposit
                    self._pending_event_option = None
                    if self._pending_event_target is None:
                        raise Exception("Missing _pending_event_target for FANGIO_SH option")

                    st = self._pending_event_target.get("stage", "SPACE1")
                    space_id = self._pending_event_target.get("space")
                    picked = self._pending_event_target.get("picked") or []
                    sp = self.board.spaces[int(space_id)]

                    if opt == 0:
                        if sp.closed_casinos > 0:
                            sp.closed_casinos -= 1
                            sp.pieces[10] += 1
                            sp.update_control()
                            print(f" -> Fangio (Sh): Opened Casino in {sp.name}.")
                        else:
                            print(f" -> Fangio (Sh): No closed Casino in {sp.name}.")
                    else:
                        # Cash deposit needs faction selection
                        allowed_owners = []
                        if int(sp.pieces[0] + sp.pieces[1]) > 0:
                            allowed_owners.append(0)
                        if int(sp.pieces[2] + sp.pieces[3]) > 0:
                            allowed_owners.append(1)
                        if int(sp.pieces[5] + sp.pieces[6]) > 0:
                            allowed_owners.append(2)
                        if int(sp.pieces[8] + sp.pieces[9]) > 0:
                            allowed_owners.append(3)
                        self._pending_event_faction = {"event": "FANGIO_SH_CASH_OWNER", "allowed": allowed_owners, "space": space_id}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        # We don't finish yet, let faction selection handle continuation
                        return self.observation, reward, done, False, {}

                    # Flow for Open Casino (opt=0)
                    picked.append(int(space_id))
                    self._pending_event_target["picked"] = picked
                    self._pending_event_target["space"] = None
                    self._pending_event_target["stage"] = "SPACE2" if st == "SPACE1" else "DONE"

                    if self._pending_event_target["stage"] != "DONE":
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    else:
                        self._pending_event_target = None
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        return self.observation, reward, done, False, {}

                elif event == "MANIFESTO_UN_PIECE":
                    # Continue MANIFESTO_UN after choosing which piece type to place.
                    self._pending_event_option = None
                    pending_target = self._pending_event_target
                    if pending_target is None or pending_target.get("event") != "MANIFESTO_UN":
                        raise Exception("Manifesto (Un): missing pending target for piece choice")

                    f_idx = int(pending_target.get("f_idx", 0))
                    count = int(pending_target.get("count", 0))
                    pos = int(pending_target.get("pos", 0))
                    order = list(pending_target.get("order", [0, 1, 2, 3]))
                    space_id = pending_target.get("space")
                    if space_id is None:
                        raise Exception("Manifesto (Un): missing space for piece choice")

                    sp = self.board.spaces[int(space_id)]
                    faction = self.players[f_idx]

                    # opt meanings:
                    # Govt: 0=Troop, 1=Police, 2=Base
                    # M26/DR: 0=Guerrilla, 1=Base
                    # Syndicate: 0=Guerrilla
                    if f_idx == 0:
                        if opt == 0 and int(faction.available_forces[0]) > 0:
                            self.board.add_piece(int(space_id), 0, 0)
                            faction.available_forces[0] -= 1
                        elif opt == 1 and int(faction.available_forces[1]) > 0:
                            self.board.add_piece(int(space_id), 0, 1)
                            faction.available_forces[1] -= 1
                        elif opt == 2 and int(faction.available_bases) > 0:
                            self.board.add_piece(int(space_id), 0, 2)
                            faction.available_bases -= 1
                        else:
                            raise Exception("Manifesto (Un): selected Govt piece not available")
                    elif f_idx in [1, 2]:
                        if opt == 0 and int(faction.available_forces[0]) > 0:
                            self.board.add_piece(int(space_id), f_idx, 0)
                            faction.available_forces[0] -= 1
                        elif opt == 1 and int(faction.available_bases) > 0:
                            self.board.add_piece(int(space_id), f_idx, 2)
                            faction.available_bases -= 1
                        else:
                            raise Exception("Manifesto (Un): selected Insurgent piece not available")
                    else:
                        if opt == 0 and int(faction.available_forces[0]) > 0:
                            self.board.add_piece(int(space_id), 3, 0)
                            faction.available_forces[0] -= 1
                        else:
                            raise Exception("Manifesto (Un): selected Syndicate piece not available")

                    count += 1
                    sp.update_control()
                    print(f"   -> Manifesto (Un): {faction.name} placed piece in {sp.name} ({count}/2).")

                    pending_target["count"] = count
                    pending_target.pop("space", None)

                    if count >= 2:
                        pos += 1
                        count = 0
                        # Advance to next faction in card order that can act.
                        while pos < len(order):
                            cand = int(order[pos])
                            # Must have available non-Casino pieces and at least one space with an existing piece.
                            if cand == 0:
                                has_avail = int(self.players[0].available_forces[0] + self.players[0].available_forces[1] + self.players[0].available_bases) > 0
                                has_space = any(int(sp2.pieces[0] + sp2.pieces[1] + sp2.govt_bases) > 0 for sp2 in self.board.spaces)
                            elif cand == 1:
                                has_avail = int(self.players[1].available_forces[0] + self.players[1].available_bases) > 0
                                has_space = any(int(sp2.pieces[2] + sp2.pieces[3] + sp2.pieces[4]) > 0 for sp2 in self.board.spaces)
                            elif cand == 2:
                                has_avail = int(self.players[2].available_forces[0] + self.players[2].available_bases) > 0
                                has_space = any(int(sp2.pieces[5] + sp2.pieces[6] + sp2.pieces[7]) > 0 for sp2 in self.board.spaces)
                            else:
                                has_avail = int(self.players[3].available_forces[0]) > 0
                                has_space = any(int(sp2.pieces[8] + sp2.pieces[9] + sp2.pieces[10]) > 0 for sp2 in self.board.spaces)
                            if has_avail and has_space:
                                break
                            pos += 1

                        if pos < len(order):
                            pending_target["pos"] = pos
                            pending_target["f_idx"] = int(order[pos])
                            pending_target["count"] = 0
                            self._pending_event_target = pending_target
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                    else:
                        # Same faction still placing (count < 2).
                        pending_target["count"] = count
                        self._pending_event_target = pending_target
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    # All done.
                    self._pending_event_target = None
                    self.keep_eligible_this_action = True
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}

                elif event == "LOECHES_UN":
                    self._pending_event_option = None
                    s_id = pending.get("space")
                    sp = self.board.spaces[s_id]
                    if opt == 0:
                        self._pending_event_target = {"event": "LOECHES_UN_MARCH", "dest": s_id}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    elif opt == 1:
                        if self.players[2].available_forces[0] > 0:
                            self.board.add_piece(s_id, 2, 0)
                            self.players[2].available_forces[0] -= 1
                        print(f" -> Rodríguez Loeches (Un): DR free Rally in {sp.name}.")
                    elif opt == 2:
                        _free_ambush_against_govt(self, s_id)
                        print(f" -> Rodríguez Loeches (Un): DR free Ambush in {sp.name}!")
                    sp.update_control()

                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                elif event == "MEYER_LANSKY_UN":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    if opt == 1:
                        if space_id is None:
                            raise Exception("Meyer Lansky (Un): missing space for continuation")
                        sp = self.board.spaces[int(space_id)]
                        allowed = [f for f in range(4) if self._space_cash_by_faction(sp, f) > 0 and self._space_has_faction_pieces(sp, f)]
                        if not allowed:
                            print(" -> Meyer Lansky (Un): No cash left to transfer.")
                        else:
                            self._pending_event_target = {"event": "MEYER_LANSKY_UN", "space": space_id}
                            self._pending_event_faction = {"event": "MEYER_LANSKY_UN_SRC", "allowed": allowed, "space": space_id}
                            self.phase = PHASE_CHOOSE_TARGET_FACTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                    # opt == 0 or no valid continuation
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                elif event == "MEYER_LANSKY_SH":
                    self._pending_event_option = None
                    if opt == 1:
                        if self._has_valid_casino_move():
                            self._pending_event_target = {"event": "MEYER_LANSKY_SH", "stage": "SRC"}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                        print(" -> Meyer Lansky (Sh): No valid Casino relocations.")

                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                elif event == "MARCH_PIECE":
                    self._pending_event_option = None
                    pending_op = self._pending_op_target
                    if pending_op is None or pending_op.get("op") != "MARCH_SRC":
                        raise Exception("March piece selection missing pending march op")
                    src = pending_op.get("src")
                    dest = pending_op.get("dest")
                    piece_map = pending_op.get("piece_map") or {}
                    piece_idx = piece_map.get(opt)
                    if src is None or dest is None or piece_idx is None:
                        raise Exception("March piece selection missing src/dest")

                    moved = self._march_move_piece(src, dest, piece_idx)
                    if moved:
                        pending_op["moved"] = int(pending_op.get("moved", 0)) + 1
                        if pending_op.get("mafia") and int(piece_idx) in [8, 9]:
                            pending_op["borrowed_used"] = True

                    pending_op.pop("src", None)
                    pending_op.pop("piece_map", None)

                    if not self._march_source_ids(pending_op):
                        self._finish_march(player, pending_op)
                        return self.observation, reward, done, False, {}

                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "SWEEP_PIECE":
                    self._pending_event_option = None
                    pending_op = self._pending_op_target
                    if pending_op is None or pending_op.get("op") != "SWEEP_SRC":
                        raise Exception("Sweep piece selection missing pending sweep op")
                    src = pending_op.get("src")
                    if src is None:
                        raise Exception("Sweep piece selection missing src")

                    if opt == 0:
                        pending_op["piece_type"] = 0
                    elif opt == 1:
                        pending_op["piece_type"] = 1
                    else:
                        raise Exception("Invalid Sweep piece selection")

                    sp_src = self.board.spaces[int(src)]
                    max_count = int(sp_src.pieces[pending_op["piece_type"]])
                    allowed = [0]
                    if max_count >= 2:
                        allowed.append(1)
                    if max_count >= 3:
                        allowed.append(2)
                    self._pending_event_option = {"event": "SWEEP_COUNT", "allowed": allowed}
                    self.phase = PHASE_CHOOSE_EVENT_OPTION
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "SWEEP_COUNT":
                    self._pending_event_option = None
                    pending_op = self._pending_op_target
                    if pending_op is None or pending_op.get("op") != "SWEEP_SRC":
                        raise Exception("Sweep count selection missing pending sweep op")
                    src = pending_op.get("src")
                    dest = pending_op.get("dest")
                    piece_type = pending_op.get("piece_type")
                    if src is None or dest is None or piece_type is None:
                        raise Exception("Sweep count selection missing src/dest/piece_type")
                    sp_src = self.board.spaces[int(src)]
                    max_count = int(sp_src.pieces[int(piece_type)])
                    if max_count <= 0:
                        raise Exception("Sweep count selection has no pieces to move")
                    if opt == 0:
                        move_count = 1
                    elif opt == 1:
                        move_count = min(2, max_count)
                    else:
                        move_count = max_count
                    moved = self._move_pieces_with_cash(int(src), int(dest), 0, int(piece_type), move_count)
                    if moved > 0:
                        pending_op["moved"] = int(pending_op.get("moved", 0)) + moved
                    pending_op.pop("src", None)
                    pending_op.pop("piece_type", None)

                    if not self._sweep_sources(pending_op):
                        self._finish_sweep(player, pending_op)
                        return self.observation, reward, done, False, {}

                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "GARRISON_COUNT":
                    self._pending_event_option = None
                    pending_op = self._pending_op_target
                    if pending_op is None or pending_op.get("op") != "GARRISON_SRC":
                        raise Exception("Garrison count selection missing pending garrison op")
                    src = pending_op.get("src")
                    dest = pending_op.get("dest")
                    if src is None or dest is None:
                        raise Exception("Garrison count selection missing src/dest")
                    sp_src = self.board.spaces[int(src)]
                    max_count = int(sp_src.pieces[1])
                    if max_count <= 0:
                        raise Exception("Garrison count selection has no Police to move")
                    if opt == 0:
                        move_count = 1
                    elif opt == 1:
                        move_count = min(2, max_count)
                    else:
                        move_count = max_count
                    moved = self._move_pieces_with_cash(int(src), int(dest), 0, 1, move_count)
                    if moved > 0:
                        pending_op["moved"] = int(pending_op.get("moved", 0)) + moved
                    pending_op.pop("src", None)
                    pending_op.pop("piece_type", None)

                    if not self._garrison_sources(pending_op):
                        self._finish_garrison(player, pending_op)
                        return self.observation, reward, done, False, {}

                    self.phase = PHASE_CHOOSE_TARGET_SPACE
                    advance_turn = False
                    return self.observation, reward, done, False, {}
                elif event == "BRAC_UN_PIECE":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    count = pending.get("count", 0)
                    faction = pending.get("faction")
                    if space_id is None or faction is None:
                        raise Exception("BRAC (Un): missing space/faction for piece choice")
                    sp = self.board.spaces[int(space_id)]
                    prefer_active = (opt == 1)
                    removed = self._brac_remove_guerrilla(sp, int(faction), prefer_active=prefer_active)
                    if removed:
                        count += 1
                        print(f" -> BRAC (Un): Removed guerrilla from {sp.name}.")
                    if count < 2:
                        any_g = any(any(sp.pieces[idx] > 0 for idx in [2,3,5,6,8,9]) for sp in self.board.spaces)
                        if any_g:
                            self._pending_event_target = {"event": "BRAC_UN", "count": count}
                            self.phase = PHASE_CHOOSE_TARGET_SPACE
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                elif event == "DEFECTIONS_UN_PIECE":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    enemy = pending.get("enemy_faction")
                    remaining = int(pending.get("remaining", 0))
                    if space_id is None or enemy is None:
                        raise Exception("Defections (Un): missing space/enemy for piece choice")
                    sp = self.board.spaces[int(space_id)]
                    enemy = int(enemy)
                    if enemy == 0:
                        u_idx, a_idx, b_idx = 0, 1, None
                    elif enemy == 1:
                        u_idx, a_idx, b_idx = 2, 3, 4
                    elif enemy == 2:
                        u_idx, a_idx, b_idx = 5, 6, 7
                    else:
                        u_idx, a_idx, b_idx = 8, 9, 10

                    removed = False
                    if opt == 0 and int(sp.pieces[u_idx]) > 0:
                        if enemy == 0:
                            sp.pieces[u_idx] -= 1
                        else:
                            self.board.remove_piece(int(space_id), enemy, 0)
                        removed = True
                    elif opt == 1 and int(sp.pieces[a_idx]) > 0:
                        if enemy == 0:
                            sp.pieces[a_idx] -= 1
                        else:
                            self.board.remove_piece(int(space_id), enemy, 1)
                        removed = True

                    if not removed:
                        print(" -> Defections (Un): Selected piece not available.")
                    else:
                        if enemy == 0:
                            if opt in [0, 1]:
                                self.players[0].available_forces[opt] += 1
                            elif opt == 2:
                                self.players[0].available_bases += 1
                        elif enemy == 1:
                            if opt in [0, 1]:
                                self.players[1].available_forces[0] += 1
                            elif opt == 2:
                                self.players[1].available_bases += 1
                        elif enemy == 2:
                            if opt in [0, 1]:
                                self.players[2].available_forces[0] += 1
                            elif opt == 2:
                                self.players[2].available_bases += 1
                        else:
                            if opt in [0, 1]:
                                self.players[3].available_forces[0] += 1
                            elif opt == 2:
                                self.players[3].available_bases += 1

                    if removed:
                        remaining -= 1
                        p_idx = self.current_player_num
                        if p_idx == 0:
                            if int(self.players[0].available_forces[0]) > 0 and int(self.players[0].available_forces[1]) > 0:
                                self._pending_event_target = {
                                    "event": "DEFECTIONS_UN",
                                    "space": space_id,
                                    "enemy_faction": enemy,
                                    "remaining": remaining,
                                    "stage": "RESUME",
                                }
                                self._pending_event_option = {
                                    "event": "DEFECTIONS_UN_GOVT_REPLACE_CUBE",
                                    "allowed": [0, 1],
                                    "space": space_id,
                                    "enemy_faction": enemy,
                                    "remaining": remaining,
                                }
                                self.phase = PHASE_CHOOSE_EVENT_OPTION
                                advance_turn = False
                                return self.observation, reward, done, False, {}
                            if int(self.players[0].available_forces[0]) > 0:
                                self.board.add_piece(int(space_id), 0, 0)
                                self.players[0].available_forces[0] -= 1
                            elif int(self.players[0].available_forces[1]) > 0:
                                self.board.add_piece(int(space_id), 0, 1)
                                self.players[0].available_forces[1] -= 1
                        else:
                            if self.players[p_idx].available_forces[0] > 0:
                                self.board.add_piece(int(space_id), p_idx, 0)
                                self.players[p_idx].available_forces[0] -= 1
                        sp.update_control()

                    if remaining > 0:
                        piece_opts = []
                        if int(sp.pieces[u_idx]) > 0:
                            piece_opts.append(0)
                        if int(sp.pieces[a_idx]) > 0:
                            piece_opts.append(1)
                        if piece_opts:
                            self._pending_event_target = {"event": "DEFECTIONS_UN", "space": space_id, "enemy_faction": enemy, "remaining": remaining}
                            self._pending_event_option = {
                                "event": "DEFECTIONS_UN_PIECE",
                                "allowed": piece_opts,
                                "space": space_id,
                                "enemy_faction": enemy,
                                "remaining": remaining,
                            }
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                elif event == "DEFECTIONS_UN_GOVT_REPLACE_CUBE":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    enemy = pending.get("enemy_faction")
                    remaining = int(pending.get("remaining", 0))
                    if space_id is None or enemy is None:
                        raise Exception("Defections (Un): missing space/enemy for Govt cube replacement")

                    if opt == 0 and int(self.players[0].available_forces[0]) > 0:
                        self.board.add_piece(int(space_id), 0, 0)
                        self.players[0].available_forces[0] -= 1
                    elif opt == 1 and int(self.players[0].available_forces[1]) > 0:
                        self.board.add_piece(int(space_id), 0, 1)
                        self.players[0].available_forces[1] -= 1

                    sp = self.board.spaces[int(space_id)]
                    sp.update_control()

                    if remaining > 0:
                        enemy = int(enemy)
                        if enemy == 0:
                            u_idx, a_idx = 0, 1
                        elif enemy == 1:
                            u_idx, a_idx = 2, 3
                        elif enemy == 2:
                            u_idx, a_idx = 5, 6
                        else:
                            u_idx, a_idx = 8, 9

                        piece_opts = []
                        if int(sp.pieces[u_idx]) > 0:
                            piece_opts.append(0)
                        if int(sp.pieces[a_idx]) > 0:
                            piece_opts.append(1)
                        if piece_opts:
                            self._pending_event_target = {"event": "DEFECTIONS_UN", "space": space_id, "enemy_faction": enemy, "remaining": remaining}
                            self._pending_event_option = {
                                "event": "DEFECTIONS_UN_PIECE",
                                "allowed": piece_opts,
                                "space": space_id,
                                "enemy_faction": enemy,
                                "remaining": remaining,
                            }
                            self.phase = PHASE_CHOOSE_EVENT_OPTION
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                elif event == "ECHEVERRIA_SH_PIECE":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    remaining = int(pending.get("remaining", 0))
                    if space_id is None:
                        raise Exception("Echeverría (Sh): missing space for piece choice")
                    sp = self.board.spaces[int(space_id)]
                    if opt == 0 and int(sp.pieces[5]) > 0:
                        self.board.remove_piece(int(space_id), 2, 0)
                        self.players[2].available_forces[0] += 1
                    elif opt == 1 and int(sp.pieces[6]) > 0:
                        self.board.remove_piece(int(space_id), 2, 1)
                        self.players[2].available_forces[0] += 1
                    elif opt == 2 and int(sp.pieces[7]) > 0:
                        self.board.remove_piece(int(space_id), 2, 2)
                        self.players[2].available_bases += 1
                    else:
                        print(" -> Echeverría (Sh): Selected piece not available.")
                        remaining = remaining + 1

                    remaining = max(0, remaining - 1)
                    sp.update_control()
                    print(f" -> Echeverría (Sh): Removed DR piece from {sp.name} ({2 - remaining}/2).")

                    if remaining > 0:
                        self._pending_event_target = {"event": "ECHEVERRIA_SH", "remaining": remaining}
                        self.phase = PHASE_CHOOSE_TARGET_SPACE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                elif event == "CHOMON_SH_PIECE":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    if space_id is None:
                        raise Exception("Fauré Chomón (Sh): missing space for piece choice")
                    sp = self.board.spaces[int(space_id)]
                    piece_choice = opt
                    can_replace = (
                        self.players[1].available_bases > 0 if piece_choice == 2
                        else self.players[1].available_forces[0] > 0
                    )
                    if can_replace:
                        self._pending_event_target = {"event": "CHOMON_SH", "space": space_id, "piece": piece_choice}
                        self._pending_event_option = {
                            "event": "CHOMON_SH_ACTION",
                            "allowed": [0, 1],
                            "space": space_id,
                            "piece": piece_choice,
                        }
                        self.phase = PHASE_CHOOSE_EVENT_OPTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}
                    if piece_choice == 0 and int(sp.pieces[5]) > 0:
                        self.board.remove_piece(int(space_id), 2, 0)
                        self.players[2].available_forces[0] += 1
                    elif piece_choice == 1 and int(sp.pieces[6]) > 0:
                        self.board.remove_piece(int(space_id), 2, 1)
                        self.players[2].available_forces[0] += 1
                    elif piece_choice == 2 and int(sp.pieces[7]) > 0:
                        self.board.remove_piece(int(space_id), 2, 2)
                        self.players[2].available_bases += 1
                    else:
                        print(" -> Fauré Chomón (Sh): Selected piece not available.")
                    sp.update_control()
                    print(f" -> Fauré Chomón (Sh): Removed DR piece from {sp.name}.")

                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}

                elif event == "CHOMON_SH_ACTION":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    piece_choice = pending.get("piece")
                    if space_id is None or piece_choice is None:
                        raise Exception("Fauré Chomón (Sh): missing space/piece for action choice")
                    sp = self.board.spaces[int(space_id)]
                    replaced = False
                    if piece_choice == 0 and int(sp.pieces[5]) > 0:
                        self.board.remove_piece(int(space_id), 2, 0)
                        self.players[2].available_forces[0] += 1
                        if opt == 1 and self.players[1].available_forces[0] > 0:
                            sp.pieces[2] += 1
                            self.players[1].available_forces[0] -= 1
                            replaced = True
                    elif piece_choice == 1 and int(sp.pieces[6]) > 0:
                        self.board.remove_piece(int(space_id), 2, 1)
                        self.players[2].available_forces[0] += 1
                        if opt == 1 and self.players[1].available_forces[0] > 0:
                            sp.pieces[3] += 1
                            self.players[1].available_forces[0] -= 1
                            replaced = True
                    elif piece_choice == 2 and int(sp.pieces[7]) > 0:
                        self.board.remove_piece(int(space_id), 2, 2)
                        self.players[2].available_bases += 1
                        if opt == 1 and self.players[1].available_bases > 0:
                            sp.pieces[4] += 1
                            self.players[1].available_bases -= 1
                            replaced = True
                    else:
                        print(" -> Fauré Chomón (Sh): Selected piece not available.")
                    sp.update_control()
                    if replaced:
                        print(f" -> Fauré Chomón (Sh): Replaced DR piece with M26 in {sp.name}.")
                    else:
                        print(f" -> Fauré Chomón (Sh): Removed DR piece from {sp.name}.")

                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                elif event == "MENOYO_UN_PIECE":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    if space_id is None:
                        raise Exception("Eloy Gutiérrez Menoyo (Un): missing space for piece choice")
                    sp = self.board.spaces[int(space_id)]
                    removed = self._menoyo_un_remove_piece(sp, int(opt))
                    if removed:
                        for _ in range(2):
                            if self.players[2].available_forces[0] > 0:
                                self.board.add_piece(int(space_id), 2, 0)
                                self.players[2].available_forces[0] -= 1
                        sp.update_control()
                        print(f" -> Eloy Gutiérrez Menoyo (Un): Replaced piece with 2 DR in {sp.name}.")
                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                elif event == "MENOYO_SH_PIECE":
                    self._pending_event_option = None
                    space_id = pending.get("space")
                    if space_id is None:
                        raise Exception("Eloy Gutiérrez Menoyo (Sh): missing space for piece choice")
                    sp = self.board.spaces[int(space_id)]
                    if opt == 0 and sp.pieces[5] > 0:
                        self.board.remove_piece(int(space_id), 2, 0)
                    elif opt == 1 and sp.pieces[6] > 0:
                        self.board.remove_piece(int(space_id), 2, 1)
                    else:
                        print(" -> Eloy Gutiérrez Menoyo (Sh): Selected DR piece not available.")
                    self.players[2].available_forces[0] += 1

                    allowed_factions = []
                    if self.players[1].available_forces[0] > 0:
                        allowed_factions.append(1)
                    if self.players[3].available_forces[0] > 0:
                        allowed_factions.append(3)

                    if allowed_factions:
                        self._pending_event_faction = {"event": "MENOYO_SH_FACTION", "allowed": allowed_factions, "space": space_id}
                        self.phase = PHASE_CHOOSE_TARGET_FACTION
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    sp.update_control()
                    print(f" -> Eloy Gutiérrez Menoyo (Sh): Removed DR from {sp.name}.")

                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    return self.observation, reward, done, False, {}
                else:
                    raise Exception(f"Unhandled pending option event: {event}")

            elif self.phase == PHASE_CHOOSE_TARGET_PIECE:
                choice = action - self._target_piece_action_base
                if not self._pending_cash_transfers:
                    pending_target = self._pending_event_target

                    if pending_target is not None and pending_target.get("op") == "AMBUSH_PIECE":
                        space_id = pending_target.get("space")
                        sp = self.board.spaces[space_id]
                        target_faction_id = pending_target.get("target_faction_id")
                        ambushing_faction_id = pending_target.get("ambushing_faction_id")

                        # Identify attacking underground guerrilla and flip to active
                        u_idx = 2 if ambushing_faction_id == 1 else 5
                        a_idx = 3 if ambushing_faction_id == 1 else 6
                        if sp.pieces[u_idx] > 0:
                            sp.pieces[u_idx] -= 1
                            sp.pieces[a_idx] += 1

                        if choice == 11: # Base
                            if target_faction_id == 0: sp.govt_bases -= 1
                        else:
                            sp.pieces[choice] -= 1

                        print(f" -> Ambush: Removed piece {choice} from faction {target_faction_id}")

                        # Reward 1 Underground Guerrilla only if Govt Troop or Police was removed
                        if target_faction_id == 0 and choice in [0, 1]:
                            f_idx = 1 if ambushing_faction_id == 1 else 2 # 1=M26, 2=DR
                            if self.players[f_idx].available_forces[0] > 0:
                                self.board.add_piece(space_id, f_idx, 0)
                                self.players[f_idx].available_forces[0] -= 1
                                print(f" -> Ambush vs Govt: Placed 1 Underground Guerrilla for faction {f_idx}.")

                        sp.update_control()

                        self._pending_event_target = None
                        self.phase = PHASE_CHOOSE_SPECIAL_ACTIVITY
                        self._pending_sa = True
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    if pending_target is None or pending_target.get("event") != "MEYER_LANSKY_UN":
                        raise Exception("Missing pending cash transfer in PHASE_CHOOSE_TARGET_PIECE")

                    stage = pending_target.get("stage")
                    space_id = pending_target.get("space")
                    if space_id is None:
                        raise Exception("Meyer Lansky (Un): missing space")
                    sp = self.board.spaces[int(space_id)]

                    stop_choice = (self._target_piece_action_count - 1)
                    if stage == "SRC_HOLDER":
                        if choice == stop_choice:
                            # Finish action.
                            self._pending_event_target = None
                            player.eligible = False
                            if not self.keep_eligible_this_action:
                                self.ineligible_next_card.add(self.current_player_num)
                            self.card_action_slot += 1
                            self.phase = PHASE_CHOOSE_MAIN
                            self._pending_main = None
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        if int(sp.cash_holders[int(choice)]) <= 0:
                            raise Exception("Meyer Lansky (Un): selected source holder has no cash")
                        # Check if any valid destination exists before entering DEST_HOLDER
                        has_dest = any(
                            int(sp.pieces[idx]) > 0 and int(idx) != int(choice)
                            for idx in range(len(sp.pieces))
                        )
                        if not has_dest:
                            # No destination available — auto-finish event
                            print(" -> Meyer Lansky (Un): No valid destination for cash transfer.")
                            self._pending_event_target = None
                            player.eligible = False
                            if not self.keep_eligible_this_action:
                                self.ineligible_next_card.add(self.current_player_num)
                            self.card_action_slot += 1
                            self.phase = PHASE_CHOOSE_MAIN
                            self._pending_main = None
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                        pending_target["src_holder"] = int(choice)
                        pending_target["stage"] = "DEST_HOLDER"
                        self._pending_event_target = pending_target
                        self.phase = PHASE_CHOOSE_TARGET_PIECE
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    if stage == "DEST_HOLDER":
                        src_holder = pending_target.get("src_holder")
                        if src_holder is None:
                            raise Exception("Meyer Lansky (Un): missing src holder")
                        # Handle stop action
                        if choice == stop_choice:
                            self._pending_event_target = None
                            player.eligible = False
                            if not self.keep_eligible_this_action:
                                self.ineligible_next_card.add(self.current_player_num)
                            self.card_action_slot += 1
                            self.phase = PHASE_CHOOSE_MAIN
                            self._pending_main = None
                            advance_turn = False
                            return self.observation, reward, done, False, {}
                        if int(choice) == int(src_holder):
                            raise Exception("Meyer Lansky (Un): destination cannot equal source")
                        if not self._transfer_cash_between_holders(sp, int(src_holder), int(choice)):
                            raise Exception("Meyer Lansky (Un): failed to transfer cash")
                        print(f" -> Meyer Lansky (Un): Moved Cash holder {src_holder} -> {int(choice)} in {sp.name}.")

                        pending_target.pop("src_holder", None)
                        if self._space_has_valid_cash_transfer_between_holders(sp):
                            pending_target["stage"] = "SRC_HOLDER"
                            self._pending_event_target = pending_target
                            self.phase = PHASE_CHOOSE_TARGET_PIECE
                            advance_turn = False
                            return self.observation, reward, done, False, {}

                        # No more valid transfers.
                        self._pending_event_target = None
                        player.eligible = False
                        if not self.keep_eligible_this_action:
                            self.ineligible_next_card.add(self.current_player_num)
                        self.card_action_slot += 1
                        self.phase = PHASE_CHOOSE_MAIN
                        self._pending_main = None
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    raise Exception(f"Meyer Lansky (Un): unknown stage {stage}")

                pending = self._pending_cash_transfers[0]
                space_id = int(pending.get("space_id"))
                sp = self.board.spaces[space_id]
                src_idx = int(pending.get("src_idx"))
                if choice == (self._target_piece_action_count - 1):
                    if int(sp.cash_holders[src_idx]) > 0:
                        sp.cash_holders[src_idx] -= 1
                else:
                    if int(sp.cash_holders[src_idx]) <= 0:
                        raise Exception("Cash transfer: source has no cash")
                    if int(sp.pieces[int(choice)]) <= 0:
                        raise Exception("Cash transfer: selected piece not present")
                    sp.cash_holders[src_idx] -= 1
                    sp.cash_holders[int(choice)] += 1
                self._refresh_space_cash_counts(sp)
                pending["count"] = int(pending.get("count")) - 1
                if pending["count"] <= 0:
                    self._pending_cash_transfers.popleft()
                    if self._pending_cash_transfers:
                        self.current_player_num = int(self._pending_cash_transfers[0].get("owner"))
                        player = self.players[self.current_player_num]
                    else:
                        self._cash_transfer_waiting = False
                        self._cash_transfer_active = False
                        if self._cash_transfer_return_player is not None:
                            self.current_player_num = int(self._cash_transfer_return_player)
                            player = self.players[self.current_player_num]
                        if self._cash_transfer_return_phase is not None:
                            self.phase = self._cash_transfer_return_phase
                        if self._cash_transfer_return_advance:
                            self.update_turn_pointer()
                        self._cash_transfer_return_player = None
                        self._cash_transfer_return_phase = None
                        self._cash_transfer_return_advance = False
                else:
                    self._pending_cash_transfers[0] = pending
                self.factions_acted_this_card = int(self.card_action_slot)
                scalar_reward = float(reward[self.current_player_num])
                return self.observation, scalar_reward, done, False, {"rewards": reward}

            elif self.phase == PHASE_CHOOSE_SPECIAL_ACTIVITY:
                if action == (self._main_action_base + MAIN_PASS):
                    # Skip SA by taking MAIN_PASS. If we paid for an Operation and executed no SA, offer Launder.
                    if self._maybe_start_launder():
                        advance_turn = False
                        return self.observation, reward, done, False, {}

                    player.eligible = False
                    if not self.keep_eligible_this_action:
                        self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    self._pending_sa = None
                    self._sa_free = False
                    self._sa_from_limited_ops = False
                    self._sa_restrict_op = None
                    self._sa_restrict_space = None
                    self._last_op_paid_cost = 0
                else:
                    ops_action = action - self._ops_action_base
                    op = ops_action // self.num_spaces
                    s = ops_action % self.num_spaces

                    cost = 0
                    if player.name == "GOVT":
                        if op == OP_AIR_STRIKE: cost = self.op_airstrike(s)
                        elif op == OP_ASSAULT:
                            cost = self._op_assault_impl(s, context="SA")
                            if cost is None:
                                self.phase = PHASE_CHOOSE_TARGET_FACTION
                                advance_turn = False
                                cost = 0
                    elif player.name == "M26":
                        if op == OP_AMBUSH_M26:
                            cost = self.op_ambush_m26(s)
                            if cost is None:
                                return self.observation, reward, done, False, {}
                        elif op == OP_KIDNAP_M26:
                            cost = self.op_kidnap_m26(s)
                            if cost is None:
                                return self.observation, reward, done, False, {}
                    elif player.name == "DR":
                        if op == OP_ASSASSINATE_DR: cost = self.op_assassinate_dr(s)
                    elif player.name == "SYNDICATE":
                        if op == OP_BRIBE_SYN: cost = self.op_bribe_syn(s)
                        elif op == OP_CONSTRUCT_SYN: cost = self.op_construct_syn(s)
                        elif op == OP_ASSASSINATE_DR and "Hitmen_Shaded" in self.capabilities:
                            cost = self.op_assassinate_hitmen(s)

                    if not self._sa_free:
                        # Special Activities usually don't have resource costs except Bribe, but cost is returned.
                        player.resources = max(0, player.resources - cost)
                    # Any executed Special Activity prevents Launder.
                    self._last_op_paid_cost = 0
                    player.eligible = False
                    self.ineligible_next_card.add(self.current_player_num)
                    self.card_action_slot += 1
                    self.phase = PHASE_CHOOSE_MAIN
                    self._pending_main = None
                    self._pending_sa = None
                    self._sa_free = False
                    self._sa_from_limited_ops = False
                    self._sa_restrict_op = None
                    self._sa_restrict_space = None

            else:
                raise Exception(f"Invalid phase: {self.phase}")

        self.factions_acted_this_card = int(self.card_action_slot)
        if self.deck_empty: done = True
        if done:
            margins = self.victory_margins()
            ranking = self.final_victory_ranking()
            winner = self.factions_list[ranking[0]]
            print(f"\n{'='*40}")
            print(f"  GAME OVER (Round {self.rounds_taken}) — {winner} WINS!")
            print(f"  Margins: GOVT={margins[0]:+d}  M26={margins[1]:+d}  DR={margins[2]:+d}  SYN={margins[3]:+d}")
            print(f"{'='*40}")
        if self._cash_transfer_waiting and self._cash_transfer_return_player is None:
            self._cash_transfer_return_player = self.current_player_num
            self._cash_transfer_return_phase = self.phase
            self._cash_transfer_return_advance = advance_turn
        if not done and advance_turn and not self._cash_transfer_waiting:
            self.update_turn_pointer()

        # Gymnasium returns: obs, reward, terminated, truncated, info
        terminated = done
        truncated = False
        scalar_reward = float(reward[self.current_player_num])
        return self.observation, scalar_reward, terminated, truncated, {"rewards": reward}

    # --- IMPLEMENTATIONS ---
