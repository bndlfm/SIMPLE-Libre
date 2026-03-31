import numpy as np
from .constants import US_ALLIANCE_FIRM, US_ALLIANCE_RELUCTANT, US_ALLIANCE_EMBARGOED

def resolve_event(env, card_id, play_shaded):
    """
    Executes the event text for the current card.
    """
    player = env.players[env.current_player_num]
    print(f"\n--- EVENT: {env.current_card.name} (Played by {player.name}) ---")

    suffix = "SHADED" if play_shaded else "UNSHADED"
    print(f" -> Playing {suffix} Text")

    if card_id == 1: evt_armored_cars(env, play_shaded)
    elif card_id == 2: evt_guantanamo(env, play_shaded)
    elif card_id == 3: evt_eulogio_cantillo(env, play_shaded)
    elif card_id == 4: evt_sim(env, play_shaded)
    elif card_id == 5: evt_rolando_masferrer(env, play_shaded)
    elif card_id == 6: evt_sanchez_mosquera(env, play_shaded)
    elif card_id == 7: evt_election(env, play_shaded)
    elif card_id == 8: evt_general_strike(env, play_shaded)
    elif card_id == 9: evt_coup(env, play_shaded)
    elif card_id == 10: evt_map(env, play_shaded)
    elif card_id == 11: evt_batista_flees(env, play_shaded)
    elif card_id == 12: evt_brac(env, play_shaded)
    elif card_id == 13: evt_el_che(env, play_shaded)
    elif card_id == 14: evt_operation_fisherman(env, play_shaded)
    elif card_id == 15: evt_come_comrades(env, play_shaded)
    elif card_id == 16: evt_larrazabal(env, play_shaded)
    elif card_id == 17: evt_alberto_bayo(env, play_shaded)
    elif card_id == 18: evt_pact_of_caracas(env, play_shaded)
    elif card_id == 19: evt_sierra_maestra_manifesto(env, play_shaded)
    elif card_id == 20: evt_the_twelve(env, play_shaded)
    elif card_id == 21: evt_fangio(env, play_shaded)
    elif card_id == 22: evt_raul(env, play_shaded)
    elif card_id == 23: evt_radio_rebelde(env, play_shaded)
    elif card_id == 24: evt_vilma_espin(env, play_shaded)
    elif card_id == 25: evt_escapade(env, play_shaded)
    elif card_id == 26: evt_rodriguez_loeches(env, play_shaded)
    elif card_id == 27: evt_echeverria(env, play_shaded)
    elif card_id == 28: evt_morgan(env, play_shaded)
    elif card_id == 29: evt_faure_chomon(env, play_shaded)
    elif card_id == 30: evt_the_guerrilla_life(env, play_shaded)
    elif card_id == 31: evt_escopeteros(env, play_shaded)
    elif card_id == 32: evt_resistencia_civica(env, play_shaded)
    elif card_id == 33: evt_carlos_prio(env, play_shaded)
    elif card_id == 34: evt_us_speaking_tour(env, play_shaded)
    elif card_id == 35: evt_defections(env, play_shaded)
    elif card_id == 36: evt_eloy_gutierrez_menoyo(env, play_shaded)
    elif card_id == 37: evt_herbert_matthews(env, play_shaded)
    elif card_id == 38: evt_meyer_lansky(env, play_shaded)
    elif card_id == 39: evt_turismo(env, play_shaded)
    elif card_id == 40: evt_ambassador_smith(env, play_shaded)
    elif card_id == 41: evt_fat_butcher(env, play_shaded)
    elif card_id == 42: evt_llano(env, play_shaded)
    elif card_id == 43: evt_mafia_offensive(env, play_shaded)
    elif card_id == 44: evt_rebel_air_force(env, play_shaded)
    elif card_id == 45: evt_anastasia(env, play_shaded)
    elif card_id == 46: evt_sinatra(env, play_shaded)
    elif card_id == 47: evt_pact_of_miami(env, play_shaded)
    elif card_id == 48: evt_santo_trafficante_jr(env, play_shaded)
    else: print(f"Event {card_id} not implemented yet.")
    return 0


# --- HELPERS ---
def _shift_alignment(space, toward_neutral=False, toward_active_opp=False):
    """
    Handles the 5-step alignment spectrum:
    Act Supp (1,T) <-> Pas Supp (1,F) <-> Neu (0,F) <-> Pas Opp (2,F) <-> Act Opp (2,T)
    """
    if toward_neutral:
        if space.alignment == 0: return # Already Neutral
        if space.support_active:
            space.support_active = False # Active -> Passive
        else:
            space.alignment = 0 # Passive -> Neutral

    elif toward_active_opp:
        if space.alignment == 1: # Support
            if space.support_active: space.support_active = False # Act Supp -> Pas Supp
            else: space.alignment = 0 # Pas Supp -> Neu
        elif space.alignment == 0:
            space.alignment = 2; space.support_active = False # Neu -> Pas Opp
        elif space.alignment == 2 and not space.support_active:
            space.support_active = True # Pas Opp -> Act Opp


# --- CARD 1: ARMORED CARS ---
def evt_armored_cars(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): 26July or DR free Marches into a space and free Ambushes there (even if Active).
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_FACTION).
        print(" -> Armored Cars (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Capability
        env.capabilities.add("ArmoredCars_Shaded")
        print(" -> Capability Added: 'ArmoredCars_Shaded'")


def _free_ambush_against_govt(env, space_id, u=2, a=3, b=4):
    # Rule 4.3.2: Ambush removes 2 enemy pieces.
    # If multiple enemies, we should ideally pause for selection.
    # But for some simple events, we might want a helper.
    # Let's transition to the generic attack logic instead of this hardcoded helper.
    return env._op_attack_insurgent(space_id, u, a, b, removals_left=2, skip_roll=True)


def _free_ambush_against_govt_bases_first(env, space_id, u=2, a=3, b=4):
    # Used by Rebel Air Force (Unshaded)
    # "Remove Bases first"
    # For now, we still use simplified priority logic but with parameterized pieces
    sp = env.board.spaces[space_id]

    # Check if there are ANY guerrillas to perform the ambush
    if int(sp.pieces[u] + sp.pieces[a]) <= 0:
        print(f" -> No guerrilla in {sp.name} to Ambush.")
        return 0

    kills = 0
    for _ in range(2):
        if sp.govt_bases > 0:
            sp.govt_bases -= 1
            env.players[0].available_bases += 1
            kills += 1
        elif sp.pieces[1] > 0:
            env.board.remove_piece(space_id, 0, 1); kills += 1
        elif sp.pieces[0] > 0:
            env.board.remove_piece(space_id, 0, 0); kills += 1
    sp.update_control()
    print(f" -> Killed {kills} Govt pieces (Bases first).")
    return 1


# --- CARD 2: GUANTANAMO BAY ---
def evt_guantanamo(env, play_shaded):
    if not play_shaded:
        # UNSHADED: 26July may Kidnap in Sierra Maestra as if City.
        # Implemented as a capability checked by Ops masking.
        env.capabilities.add("Guantanamo_Unshaded")
        print(" -> Capability Added: 'Guantanamo_Unshaded'")
    else:
        # SHADED: Until Propaganda, Air Strike removes 2 pieces and allowed even if Embargoed.
        # Implemented as a capability checked by Ops masking.
        env.capabilities.add("Guantanamo_Shaded")
        print(" -> Capability Added: 'Guantanamo_Shaded'")


# --- CARD 3: EULOGIO CANTILLO ---
def evt_eulogio_cantillo(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Select a space with Troops. A Faction free Marches all its Guerrillas out,
        # then flips them Underground.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Cantillo (Un): Handled by agent-driven targeting.")
    else:
        # SHADED: Select a Province or City with Troops. They free Sweep in place, then free Assault.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Cantillo (Sh): Handled by agent-driven targeting.")


# --- CARD 4: S.I.M. ---
def evt_sim(env, play_shaded):
    if play_shaded:
        # SHADED: Capability for Police Movement/Sweep.
        env.capabilities.add("SIM_Shaded")
        print(" -> Capability Added: 'SIM_Shaded' (Police Move/Sweep)")
    else:
        # UNSHADED handled by agent-driven targeting in env.py.
        print(" -> S.I.M (Un): Handled by agent-driven targeting.")


# --- CARD 5: ROLANDO MASFERRER ---
def evt_rolando_masferrer(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Set Province w/ Troops + 1 Adjacent to Passive Opposition.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Masferrer (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Capability "Masferrer_Shaded"
        # Sweep may free Assault 1 space.
        env.capabilities.add("Masferrer_Shaded")
        print(" -> Capability Added: 'Masferrer_Shaded' (Free Assault after Sweep)")


# --- CARD 6: SANCHEZ MOSQUERA ---
def evt_sanchez_mosquera(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Remove all Troops from a Mountain space.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Mosquera (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Capability "Mosquera_Shaded"
        # Assault treats Mountain as City (Kill All).
        env.capabilities.add("Mosquera_Shaded")
        print(" -> Capability Added: 'Mosquera_Shaded' (Better Mountain Assault)")


# --- CARD 7: ELECTION ---
def evt_election(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Place 1 Guerrilla in each City.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_FACTION).
        print(" -> Election (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Set a City to Neutral. Aid +10.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Election (Sh): Handled by agent-driven targeting.")

        env.shift_aid(10)
        print(f" -> Aid +10 (Aid={env.aid}).")


# --- CARD 8: GENERAL STRIKE ---
def evt_general_strike(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): In each City, shift 1 level toward Neutral AND place 1 Guerrilla.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_FACTION).
        print(" -> General Strike (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Set a City to Active Support. Activate ALL Guerrillas there. Open 1 Casino.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> General Strike (Sh): Handled by agent-driven targeting.")


# --- CARD 9: COUP ---
def evt_coup(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Shift all Govt Control spaces 1 level toward Neutral. US Alliance +1.
        print(" -> Coup (Un): Shifting Govt Controlled spaces...")
        count = 0
        for s in env.board.spaces:
            # Update control to be sure
            s.update_control()
            if s.controlled_by == 1: # Govt
                _shift_alignment(s, toward_neutral=True)
                count += 1
        print(f" -> Shifted {count} spaces.")

        if env.us_alliance < US_ALLIANCE_EMBARGOED:
            env.shift_us_alliance(1)
            print(f" -> US Alliance worsens to {env.us_alliance}.")

    else:
        # SHADED (Govt): Activate and free Assault all DR pieces in Cities with cubes. US Alliance -1.
        print(" -> Coup (Sh): Purging Directorio in Cities...")
        if env.us_alliance > US_ALLIANCE_FIRM:
            env.shift_us_alliance(-1)
            print(f" -> US Alliance improves to {env.us_alliance}.")

        for s in env.board.spaces:
            has_cubes = (s.pieces[0] + s.pieces[1]) > 0
            has_dr = (s.pieces[5] + s.pieces[6] + s.pieces[7]) > 0

            if s.type == 0 and has_cubes and has_dr:
                print(f" -> Purging {s.name}...")
                # 1. Activate DR (5->6)
                u_dr = s.pieces[5]
                if u_dr > 0:
                    s.pieces[5] = 0
                    s.pieces[6] += u_dr
                    env._move_cash_between_piece_indices(s, 5, 6, u_dr)

                # 2. Free Assault (Targeting DR specifically? Rule says "Assault all DR pieces")
                # We can reuse standard assault but it targets M26 too.
                # Let's write a mini-assault loop targeting ONLY DR (Indices 5,6,7)
                sim = "SIM_Shaded" in env.capabilities
                troops = s.pieces[0]
                police = s.pieces[1]
                killers = troops + (police if sim else 0)
                u_killers = 0 if sim else police

                killed = 0

                for idx in [5]:
                    while u_killers > 0 and s.pieces[idx] > 0:
                        env.board.remove_piece(s.id, 2, 0)
                        u_killers -= 1
                        killed += 1

                if killers > 0:
                    for idx in [6]:
                        while killers > 0 and s.pieces[idx] > 0:
                            env.board.remove_piece(s.id, 2, 1)
                            killers -= 1
                            killed += 1

                if killers > 0:
                    for idx in [5]:
                        while killers > 0 and s.pieces[idx] > 0:
                            env.board.remove_piece(s.id, 2, 0)
                            killers -= 1
                            killed += 1

                if killers > 0:
                    gs = s.pieces[5] + s.pieces[6]
                    while killers > 0 and s.pieces[7] > 0 and gs == 0:
                        env.board.remove_piece(s.id, 2, 2)
                        killers -= 1
                        killed += 1

                print(f"   -> Killed {killed} DR pieces.")


# --- CARD 10: MAP ---
def evt_map(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Replace a cube with any 2 Guerrillas.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> MAP (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Govt LimOps may include free Special Activity.
        env.capabilities.add("MAP_Shaded")
        print(" -> Capability Added: 'MAP_Shaded' (Free SA with LimOp)")


# --- CARD 11: BATISTA FLEES ---
def evt_batista_flees(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Government Resources -10. Select and remove a die roll of Troops.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Batista Flees (Un): Handled by agent-driven targeting.")
    else:
        # SHADED: Unplayable
        print(" -> Batista Flees (Sh): UNPLAYABLE - No effect.")


# --- CARD 12: BRAC ---
def evt_brac(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Govt plays this): Remove any 2 Guerrillas.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> BRAC (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Place 1 Police anywhere. Add lesser of +6 or Aid to Govt Resources.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> BRAC (Sh): Handled by agent-driven targeting.")


# --- CARD 13: EL CHE ---
def evt_el_che(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Capability - First March group moves extra.
        env.capabilities.add("ElChe_Unshaded")
        print(" -> Capability Added: 'ElChe_Unshaded' (Extra March movement)")
    else:
        # SHADED: Unplayable
        print(" -> El Che (Sh): UNPLAYABLE - No effect.")


# --- CARD 14: OPERATION FISHERMAN ---
def evt_operation_fisherman(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Place M26 Base and Guerrilla in Pinar del Río (0).
        target = 0  # Pinar del Río
        s = env.board.spaces[target]

        if env.players[1].available_bases > 0:
            s.pieces[4] += 1  # M26 Base
            env.players[1].available_bases -= 1
            print(f" -> Fisherman (Un): Placed M26 Base in {s.name}.")

        if env.players[1].available_forces[0] > 0:
            env.board.add_piece(target, 1, 0)  # M26 Underground
            env.players[1].available_forces[0] -= 1
            print(f" -> Fisherman (Un): Placed M26 Guerrilla in {s.name}.")
    else:
        # SHADED (Govt): Shift Pinar del Río 2 levels toward Support.
        target = 0
        s = env.board.spaces[target]
        for _ in range(2):
            _shift_toward_support(s)
        print(f" -> Fisherman (Sh): Shifted {s.name} toward Support.")


# --- CARD 15: COME COMRADES! ---
def evt_come_comrades(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Place 3 M26 Guerrillas anywhere.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Come Comrades! (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Add lesser of Aid or +10 to Government Resources. Then Aid +5.
        add_amt = min(int(env.aid), 10)
        env.players[0].resources = min(49, env.players[0].resources + add_amt)
        env.shift_aid(5)
        print(f" -> Come Comrades! (Sh): Govt Resources +{add_amt}, Aid +5 (Aid={env.aid}).")


# --- CARD 16: LARRAZÁBAL ---
def evt_larrazabal(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): Place M26 Base in Oriente (9).
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Larrazábal (Un): Handled by agent-driven targeting.")
    else:
        # SHADED (Govt): Remove one 26July Base.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Larrazábal (Sh): Handled by agent-driven targeting.")



# --- CARD 17: ALBERTO BAYO ---
def evt_alberto_bayo(env, play_shaded):
    if not play_shaded:
        # UNSHADED (Rebel): 26July or DR free Rallies in each space it has a Base.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_FACTION).
        print(" -> Alberto Bayo (Un): Handled by agent-driven targeting.")

    else:
        # SHADED (Govt): All 26July Guerrillas Active.
        count = 0
        for s in env.board.spaces:
            u_m26 = s.pieces[2]
            if u_m26 > 0:
                s.pieces[2] = 0
                s.pieces[3] += u_m26
                count += u_m26
        print(f" -> Alberto Bayo (Sh): Activated {count} M26 Guerrillas.")
        # 26July Ineligible through next card.
        env.players[1].eligible = False
        env.ineligible_through_next_card.add(1)


# --- CARD 18: PACT OF CARACAS ---
def evt_pact_of_caracas(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Capability - M26/DR don't remove each other.
        env.capabilities.add("PactOfCaracas_Unshaded")
        print(" -> Capability Added: 'PactOfCaracas_Unshaded'")
        env.keep_eligible_this_action = True
    else:
        print(" -> Pact of Caracas (Sh): UNPLAYABLE.")


# --- CARD 19: SIERRA MAESTRA MANIFESTO ---
def evt_sierra_maestra_manifesto(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Sierra Maestra Manifesto ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 20: THE TWELVE ---
def evt_the_twelve(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> The Twelve ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")




# --- CARD 22: RAÚL ---
def evt_raul(env, play_shaded):
    if not play_shaded:
        env.capabilities.add("Raul_Unshaded")
        print(" -> Capability Added: 'Raul_Unshaded' (M26 Reroll)")
    else:
        # SHADED: Govt Momentum.
        # We assume this is a passive capability handled in resource phase or similar.
        # For now, just mark it.
        env.capabilities.add("Raul_Shaded")
        print(" -> Capability Added: 'Raul_Shaded' (Kidnap Resources x2)")


# --- CARD 23: RADIO REBELDE ---
def evt_radio_rebelde(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Radio Rebelde ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 24: VILMA ESPÍN ---
def evt_vilma_espin(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Vilma Espín ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 25: ESCAPADE ---
def evt_escapade(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Escapade ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 26: RODRÍGUEZ LOECHES ---
def evt_rodriguez_loeches(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Rodríguez Loeches ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 27: ECHEVERRÍA ---
def evt_echeverria(env, play_shaded):
    if not play_shaded:
        # UNSHADED: now handled by agent-driven targeting in env.py.
        print(" -> Echeverría (Un): Handled by agent-driven targeting.")
    else:
        # SHADED: now handled by agent-driven targeting in env.py.
        print(" -> Echeverría (Sh): Handled by agent-driven targeting.")


# --- CARD 28: MORGAN ---
def evt_morgan(env, play_shaded):
    if not play_shaded:
        # UNSHADED: DR Guerrillas may March 2 adjacent spaces.
        env.capabilities.add("Morgan_Unshaded")
        print(" -> Capability Added: 'Morgan_Unshaded' (DR March 2).")
    else:
        # SHADED: handled by agent-driven targeting in env.py.
        print(" -> Morgan (Sh): Handled by agent-driven targeting.")


# --- CARD 29: FAURÉ CHOMÓN ---
def evt_faure_chomon(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Fauré Chomón ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 30: THE GUERRILLA LIFE ---
def evt_the_guerrilla_life(env, play_shaded):
    if not play_shaded:
        env.capabilities.add("GuerrillaLife_Unshaded")
        print(" -> Capability Added: 'GuerrillaLife_Unshaded'.")
    else:
        # Now handled by agent-driven targeting in env.py.
        print(" -> The Guerrilla Life (Sh): Handled by agent-driven targeting.")


# --- CARD 31: ESCOPETEROS ---
def evt_escopeteros(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Escopeteros ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 32: RESISTENCIA CÍVICA ---
def evt_resistencia_civica(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Resistencia Cívica ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 33: CARLOS PRÍO ---
def evt_carlos_prio(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Carlos Prío ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 34: US SPEAKING TOUR ---
def evt_us_speaking_tour(env, play_shaded):
    if play_shaded:
        # SHADED: Govt Resources + min(8, Aid). Then Aid +8.
        add_amt = min(8, int(env.aid))
        env.players[0].resources = min(49, int(env.players[0].resources) + add_amt)
        print(f" -> US Speaking Tour (Sh): Govt Resources +{add_amt} (Aid={env.aid}).")
        env.shift_aid(8)
        print(f" -> US Speaking Tour (Sh): Aid +8 (Aid={env.aid}).")
    else:
        # UNSHADED handled by agent-driven targeting in env.py.
        print(" -> US Speaking Tour (Un): Handled by agent-driven targeting.")


# --- CARD 35: DEFECTIONS ---
def evt_defections(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Defections ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 36: ELOY GUTIÉRREZ MENOYO ---
def evt_eloy_gutierrez_menoyo(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Eloy Gutiérrez Menoyo ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 37: HERBERT MATTHEWS ---
def evt_herbert_matthews(env, play_shaded):
    if not play_shaded:
        # UNSHADED: M26 Res +5. Aid -6.
        print(" -> Matthews (Un): M26 +5 Res, Govt -6 Res.")
        env.players[1].resources += 5
        env.shift_aid(-6)
        print(f" -> Aid -6 (Aid={env.aid}).")
    else:
        # SHADED: Aid +10. DR +3. Syndicate +5.
        env.shift_aid(10)
        env.players[2].resources = min(49, int(env.players[2].resources) + 3)
        env.players[3].resources = min(49, int(env.players[3].resources) + 5)
        print(f" -> Matthews (Sh): Aid +10 (Aid={env.aid}).")
        print(" -> Matthews (Sh): DR +3 Res, Syndicate +5 Res.")


# --- CARD 21: FANGIO ---
def evt_fangio(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Fangio ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 38: MEYER LANSKY ---
def evt_meyer_lansky(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Transfer Cash.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Meyer Lansky (Un): Handled by agent-driven targeting.")
    else:
        # SHADED: Syndicate relocates any Casinos anywhere. All Casinos open.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Meyer Lansky (Sh): Handled by agent-driven targeting.")


# --- CARD 39: TURISMO ---
def evt_turismo(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Support 1 level toward Neutral each Casino space.
        print(" -> Turismo (Un): Casino spaces -> Neutral.")
        for s in env.board.spaces:
            if s.pieces[10] > 0 or int(getattr(s, "closed_casinos", 0)) > 0: # Casino
                _shift_alignment(s, toward_neutral=True)
                print(f"   -> Shifted {s.name}.")
    else:
        # SHADED: Govt and Syndicate each add +3 per open Casino space with Police.
        spaces = 0
        for s in env.board.spaces:
            if int(s.pieces[10]) > 0 and int(s.pieces[1]) > 0:
                spaces += 1
        add_amt = 3 * spaces
        env.players[0].resources = min(49, int(env.players[0].resources) + add_amt)
        env.players[3].resources = min(49, int(env.players[3].resources) + add_amt)
        print(f" -> Turismo (Sh): Govt & Syn +{add_amt} Res.")


# --- CARD 40: AMBASSADOR SMITH ---
def evt_ambassador_smith(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Shift US Alliance 1 box down (worse). Leave Aid the same.
        if env.us_alliance < US_ALLIANCE_EMBARGOED:
            env.shift_us_alliance(1)
            print(f" -> Ambassador Smith (Un): US Alliance worsens ({env.us_alliance}).")
    else:
        # SHADED: Shift US Alliance 1 box up (better). Aid +9.
        if env.us_alliance > US_ALLIANCE_FIRM:
            env.shift_us_alliance(-1)
            print(f" -> Ambassador Smith (Sh): US Alliance improves ({env.us_alliance}).")
        env.shift_aid(9)
        print(f" -> Aid +9 (Aid={env.aid}).")
        add_amt = min(9, int(env.aid) // 2)
        env.players[3].resources = min(49, int(env.players[3].resources) + add_amt)
        print(f" -> Ambassador Smith (Sh): Syndicate +{add_amt} Res.")


# --- CARD 41: FAT BUTCHER ---
def evt_fat_butcher(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Close 1 Casino or Aid -8.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_EVENT_OPTION + PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Fat Butcher (Un): Handled by agent-driven targeting.")
    else:
        # SHADED: Syndicate free Ambushes and opens 1 closed Casino.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Fat Butcher (Sh): Handled by agent-driven targeting.")


# --- CARD 42: LLANO ---
def evt_llano(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Place a 26July Base and any Guerrilla in a City.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Llano (Un): Handled by agent-driven targeting.")
    else:
        # SHADED: Select a City. Remove Opposition and place an open Casino.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Llano (Sh): Handled by agent-driven targeting.")


# --- CARD 43: MAFIA OFFENSIVE ---
def evt_mafia_offensive(env, play_shaded):
    if not play_shaded:
        # UNSHADED: handled by agent-driven targeting in env.py.
        print(" -> Mafia Offensive (Un): Handled by agent-driven targeting.")
    else:
        # SHADED: Capability - Hitmen: Syndicate may Assassinate as if DR.
        env.capabilities.add("Hitmen_Shaded")
        print(" -> Capability Added: 'Hitmen_Shaded'")

# --- CARD 44: REBEL AIR FORCE ---
def evt_rebel_air_force(env, play_shaded):
    if not play_shaded:
        # UNSHADED: 26July or DR Guerrilla (Active or not) free Ambushes.
        # Now handled by agent-driven targeting in env.py (PHASE_CHOOSE_TARGET_SPACE).
        print(" -> Rebel Air Force (Un): Handled by agent-driven targeting.")
    else:
        # SHADED: Rebels purchase: Select 26July or DR and transfer 1 die roll Resources.
        print(" -> Rebel Air Force (Sh): M26/DR transfer Resources.")

def evt_anastasia(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Close all Casinos in Havana. Syn Resources -5.
        print(" -> Anastasia (Un): Close Havana Casinos, Syn Res -5.")
        havana = env.board.spaces[3]
        closed = int(havana.pieces[10])
        havana.pieces[10] = 0
        havana.closed_casinos += closed
        havana.update_control()
        env.players[3].resources = max(0, env.players[3].resources - 5)
    else:
        # SHADED: Syndicate Resources +10.
        print(" -> Anastasia (Sh): Syn Res +10.")
        env.players[3].resources = min(49, int(env.players[3].resources) + 10)


# --- CARD 46: SINATRA ---
def evt_sinatra(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Syndicate Resources -6.
        print(" -> Sinatra (Un): Syn Res -6.")
        env.players[3].resources = max(0, env.players[3].resources - 6)
    else:
        # SHADED: Place an open Casino in Havana regardless of stacking. Place 1 Cash with Police there.
        print(" -> Sinatra (Sh): Open Casino Havana.")
        havana = env.board.spaces[3]
        havana.pieces[10] += 1
        if env.players[3].available_bases > 0:
            env.players[3].available_bases -= 1
        havana.update_control()

        if int(havana.pieces[1]) > 0:
            env._add_cash_marker(havana, 3, forced_holder_idx=1)
        else:
            print(" -> Sinatra (Sh): No Police in Havana to hold Cash.")


# --- CARD 47: PACT OF MIAMI ---
def evt_pact_of_miami(env, play_shaded):
    # Now handled by agent-driven targeting in env.py.
    print(f" -> Pact of Miami ({'Sh' if play_shaded else 'Un'}): Handled by agent-driven targeting.")


# --- CARD 48: SANTO TRAFFICANTE, JR ---
def evt_santo_trafficante_jr(env, play_shaded):
    if not play_shaded:
        # UNSHADED: Syndicate Resources –10. All Syn Guerrillas Active.
        print(" -> Trafficante (Un): Syn Res -10, Activate Syn.")
        env.players[3].resources = max(0, env.players[3].resources - 10)
        for s in env.board.spaces:
            u_syn = s.pieces[8]
            s.pieces[8] = 0
            s.pieces[9] += u_syn
    else:
        # SHADED: Capability - Old-time mobster: Underground Syn block Skim.
        env.capabilities.add("Trafficante_Shaded")
        print(" -> Capability Added: 'Trafficante_Shaded'")


# --- HELPER: Shift toward Support ---
def _shift_toward_support(space):
    """
    Opposite of toward_neutral - shifts toward Active Support.
    """
    if space.alignment == 2:  # Opposition
        if space.support_active:
            space.support_active = False  # Active Opp -> Passive Opp
        else:
            space.alignment = 0  # Passive Opp -> Neutral
    elif space.alignment == 0:
        space.alignment = 1
        space.support_active = False  # Neutral -> Passive Support
    elif space.alignment == 1 and not space.support_active:
        space.support_active = True  # Passive Support -> Active Support
