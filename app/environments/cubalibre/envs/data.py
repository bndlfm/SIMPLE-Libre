"""
CUBA LIBRE EVENT DECK DATA
"""

def parse_order(order_str):
    # RETURNS: List of Faction Indices [0, 1, 2, 3] based on string char
    # G=Govt(0), M=26July(1), D=Directorate(2), S=Syndicate(3)
    mapping = {
        'G': 0,
        'M': 1, 
        'D': 2,
        'S': 3
    }
    return [mapping[char] for char in order_str if char in mapping]

# Event Data (1-48)
EVENT_DECK_DATA = {
    1: {
        "name": "Armored Cars",
        "order": parse_order("GMDS"),
        "unshaded": "In rebel service: 26July or DR free Marches into a space and free Ambushes there (even if Active).",
        "shaded": "Delivered: Until Propaganda, before Assault, move Troops to Assault spaces from other spaces."
    },
    2: {
        "name": "Guantánamo Bay",
        "order": parse_order("GMDS"),
        "unshaded": "Base personnel targeted: 26July may Kidnap in Sierra Maestra as if City.",
        "shaded": "US airfield: Until Propaganda, Air Strike removes 2 pieces and allowed even if Embargoed."
    },
    3: {
        "name": "Eulogio Cantillo",
        "order": parse_order("GMSD"),
        "unshaded": "General seals truce: Select a space with Troops. A Faction free Marches all its Guerrillas out, then flips them Underground.",
        "shaded": "Dictator backs general’s offensive: Select a Province or City with Troops. They free Sweep in place, then free Assault."
    },
    4: {
        "name": "S.I.M.",
        "order": parse_order("GMSD"),
        "unshaded": "Word of torture: Remove Support from a space with no Police.",
        "shaded": "Military intelligence gleans leads: Until next Propaganda, Police Sweep and Assault as if Troops."
    },
    5: {
        "name": "Rolando Masferrer",
        "order": parse_order("GDMS"),
        "unshaded": "Brutal commander: Set a Province with Troops and 1 adjacent Province to Passive Opposition.",
        "shaded": "Paramilitaries: Sweep may free Assault 1 space as its Special Activity (until Propaganda)."
    },
    6: {
        "name": "Sánchez Mosquera",
        "order": parse_order("GDMS"),
        "unshaded": "Popular colonel wounded: Remove all Troops from a Mountain space (to available).",
        "shaded": "Effective army commander: Until next Propaganda, Assault treats Mountain as City."
    },
    7: {
        "name": "Election",
        "order": parse_order("GDSM"),
        "unshaded": "Postponed! Rebel ranks grow: Place 1 Guerrilla in each City.",
        "shaded": "Scheduled! Batista bows to US pressure: Set a City to Neutral. Aid +10"
    },
    8: {
        "name": "General Strike",
        "order": parse_order("GDSM"),
        "unshaded": "Widespread disruption: In each City, shift 1 level toward Neutral and place any 1 Guerrilla.",
        "shaded": "Strike fails, shops open: Set a City to Active Support and Activate all Guerrillas there. Open any 1 closed Casino."
    },
    9: {
        "name": "Coup",
        "order": parse_order("GSMD"),
        "unshaded": "Batista ousted!: Shift all Govt Control spaces 1 level toward Neutral. US Alliance up 1 box.",
        "shaded": "US-backed plot discovered: Activate and free Assault all DR pieces in Cities with cubes. US Alliance down 1 box."
    },
    10: {
        "name": "MAP",
        "order": parse_order("GSMD"),
        "unshaded": "Arms shipment stolen: Replace a cube with any 2 Guerrillas.",
        "shaded": "US training: Govt may accompany LimOps with a free Special Activity."
    },
    11: {
        "name": "Batista Flees",
        "order": parse_order("GSDM"),
        "unshaded": "US forces dictator out: Government Resources –10. Select and remove a die roll of Troops. US Alliance 1 box up. Aid +10. Government Redeploys as in Propaganda round.",
        "shaded": ""
    },
    12: {
        "name": "BRAC",
        "order": parse_order("GSDM"),
        "unshaded": "Anti-subversion agency: Remove any 2 Guerrillas.",
        "shaded": "CIA trains political police: Place 1 Police anywhere. Add lesser of +6 or Aid to Government Resources."
    },
    13: {
        "name": "El Che",
        "order": parse_order("MGDS"),
        "unshaded": "Inspired military leader: The first group of Guerrillas to move on each 26July March operation flips Underground",
        "shaded": ""
    },
    14: {
        "name": "Operation Fisherman",
        "order": parse_order("MGDS"),
        "unshaded": "2nd invasion: Place a 26July Base and Guerrilla in Pinar del Río.",
        "shaded": "Locals resent being drawn in: Shift Pinar del Río 2 levels toward Active Support."
    },
    15: {
        "name": "Come Comrades!",
        "order": parse_order("MGSD"),
        "unshaded": "Communist recruits: Place 3 26July Guerrillas anywhere.",
        "shaded": "Soviet influence suspected: Add lesser of Aid or +10 to Government Resources. Then Aid +5."
    },
    16: {
        "name": "Larrazábal",
        "order": parse_order("MGSD"),
        "unshaded": "Venezuelan junta supplies arms: Place a 26July Base where there is a 26July piece.",
        "shaded": "Caracas cuts off shipments: Remove one 26July Base. 26July Resources –3."
    },
    17: {
        "name": "Alberto Bayo",
        "order": parse_order("MDGS"),
        "unshaded": "Vet trains guerrillas: 26July or DR free Rallies in each space it has a Base (as if spaces Neutral).",
        "shaded": "Mexico blocks training by Cuban expat: All 26July Guerrillas Active. 26July Ineligible through next card."
    },
    18: {
        "name": "Pact of Caracas",
        "order": parse_order("MDGS"),
        "unshaded": "INSURGENT CAPABILITY: No 26July or DR Ops or Special Activities that remove the other’s pieces or affect placed Opposition. If same player, mutual transfers allowed. If either removes 2 of its Bases at once, cancel Capability. Executing Faction stays Eligible for next card.",
        "shaded": ""
    },
    19: {
        "name": "Sierra Maestra Manifesto",
        "order": parse_order("MDSG"),
        "unshaded": "Fidel disdains elections or compromise: In card Faction order, each Faction may place 2 non-Casino pieces in a space where they already have a piece. Executing Faction stays Eligible.",
        "shaded": "The Manifesto rejected any political compromise and committed the insurgents the overthrow of the government. Essentially an escalation of the conflict, it may have also been Fidel’s best piece of rhetoric."
    },
    20: {
        "name": "The Twelve",
        "order": parse_order("MDSG"),
        "unshaded": "Tale of survivors inspires movement: A Faction free Marches then free Rallies at a March destination.",
        "shaded": "Granma travail presages supply challenge: Remove 1/2 rounded up of any Guerrillas from the space with the most Guerrillas."
    },
    21: {
        "name": "Fangio",
        "order": parse_order("MSGD"),
        "unshaded": "26July seizes racer: Shift a City 1 level toward Active Opposition, 2 levels if a 26July piece is there.",
        "shaded": "Famous driver popularizes Cuba: In 2 spaces with any Casinos, open a closed Casino or place 1 Cash with a Guerrilla or cube."
    },
    22: {
        "name": "Raúl",
        "order": parse_order("MSGD"),
        "unshaded": "INSURGENT CAPABILITY: 26July may reroll each Attack or Kidnap.",
        "shaded": "GOVERNMENT MOMENTUM: Add to Aid twice any Resources from Kidnap."
    },
    23: {
        "name": "Radio Rebelde",
        "order": parse_order("MSDG"),
        "unshaded": "Clandestine radio: Shift 2 Provinces each 1 level toward Active Opposition.",
        "shaded": "Transmitter pinpointed: Remove a 26July Base from a Province."
    },
    24: {
        "name": "Vilma Espín",
        "order": parse_order("MSDG"),
        "unshaded": "Revolutionary interlocutor: Set Sierra Maestra or an adjacent space to Active Opposition.",
        "shaded": "Raúl’s fiancé betrays urban guerrilla: Remove all 26July pieces from a City other than Havana."
    },
    25: {
        "name": "Escapade",
        "order": parse_order("DGMS"),
        "unshaded": "Yacht brings fighters: Place a DR Guerrilla and Base in either Camagüey Province or Oriente.",
        "shaded": "Resupply yacht intercepted: Remove a Directorio Base."
    },
    26: {
        "name": "Rodríguez Loeches",
        "order": parse_order("DGMS"),
        "unshaded": "DR Leader: DR places 1 Guerrilla anywhere and free Marches to, Rallies, or Ambushes there.",
        "shaded": "Inefficient administrator: Remove 1 DR Guerrilla. DR Resources –5."
    },
    27: {
        "name": "Echeverría",
        "order": parse_order("DGSM"),
        "unshaded": "Near-miss attempt on dictator’s life: Place 2 DR Guerrillas anywhere. Havana to Neutral. DR to Eligible.",
        "shaded": "Popular revolutionary dies in his “hit at the top”: Remove the 2 DR pieces closest to Havana. DR Resources –3."
    },
    28: {
        "name": "Morgan",
        "order": parse_order("DGSM"),
        "unshaded": "INSURGENT CAPABILITY: DR Guerrillas may March 2 adjacent spaces.",
        "shaded": "Backlash against Yanqui: Set a space with a DR Guerrilla to Active Support."
    },
    29: {
        "name": "Fauré Chomón",
        "order": parse_order("DMGS"),
        "unshaded": "Students take to the field: DR or 26July places a Base and 2 Guerrillas in Las Villas.",
        "shaded": "Student loyalties shift: Remove a DR piece or replace it with its 26July counterpart."
    },
    30: {
        "name": "The Guerrilla Life",
        "order": parse_order("DMGS"),
        "unshaded": "INSURGENT CAPABILITY: Hardships harden 26July fighters: All 26July Rallies flip Guerrillas Underground, even if placing.",
        "shaded": "Hardships harden student revolutionaries: Flip all DR Guerrillas Underground. Place 1 DR Guerrilla in a City."
    },
    31: {
        "name": "Escopeteros",
        "order": parse_order("DMSG"),
        "unshaded": "Locals start their own revolution: Place any non-Casino Base and any 1 Guerrilla into a Mountain.",
        "shaded": "Traditionalist countryside: Shift a Mountain space 1 level toward Support."
    },
    32: {
        "name": "Resistencia Cívica",
        "order": parse_order("DMSG"),
        "unshaded": "Urban movement backs Castro: In a City, replace all Directorio pieces with 26July counterparts.",
        "shaded": "Movement splits with Castro: In a City, replace all 26July pieces with Directorio counterparts."
    },
    33: {
        "name": "Carlos Prío",
        "order": parse_order("DSGM"),
        "unshaded": "Ex-president funnels funds: +5 DR or +5 26July Resources.",
        "shaded": "Return from exile: Select a space without Govt Control. Place a DR Base there and set it to Neutral."
    },
    34: {
        "name": "US Speaking Tour",
        "order": parse_order("DSGM"),
        "unshaded": "Expatriates invest: An Insurgent Faction adds a die roll in Resources. Each other adds +2.",
        "shaded": "An embarrassment: Add the lesser of +8 or Aid to Government Resources. Then Aid +8."
    },
    35: {
        "name": "Defections",
        "order": parse_order("DSMG"),
        "unshaded": "Disillusioned fighters: In a space already occupied by your pieces and those of an enemy, replace 2 of the enemy’s Guerrillas or cubes with your Guerrillas or cubes.",
        "shaded": "Every faction in the conflict suffered from defections, including the Syndicate, which lost employees to the insurgency and to the Government. More valuable than the manpower was the intelligence gained from these defections."
    },
    36: {
        "name": "Eloy Gutiérrez Menoyo",
        "order": parse_order("DSMG"),
        "unshaded": "Inspiring DR leader: Replace a non-DR non-Casino piece within 1 space of Las Villas with 2 DR Guerrillas.",
        "shaded": "Commander fractious: Replace a DR Guerrilla with a non-DR Guerrilla."
    },
    37: {
        "name": "Herbert Matthews",
        "order": parse_order("SGMD"),
        "unshaded": "NYTimes refutes Fidel’s death: 26July Resources +5. Aid -6.",
        "shaded": "Fidel’s survival spurs support to counterweights: Aid +10. Directorio Resources +3. Syndicate Resources +5."
    },
    38: {
        "name": "Meyer Lansky",
        "order": parse_order("SGMD"),
        "unshaded": "Wheeler dealer: Within a space, transfer any Cash among any Guerrillas or cubes.",
        "shaded": "Master mobster: Syndicate relocates any Casinos anywhere (within stacking). All Casinos open."
    },
    39: {
        "name": "Turismo",
        "order": parse_order("SGDM"),
        "unshaded": "“Ugly American”: Support 1 level toward Neutral each Casino space.",
        "shaded": "Police “protection” for tourists: Govt and Syndicate each add +3 Resources per space with open Casino and Police"
    },
    40: {
        "name": "Ambassador Smith",
        "order": parse_order("SGDM"),
        "unshaded": "Havana advocate ignored in US: Shift US Alliance 1 box down (leave Aid the same).",
        "shaded": "Blindly backing dictator: Shift US Alliance 1 box up. Aid +9. Then add lesser of +9 or half Aid (round down) to Syndicate Resources."
    },
    41: {
        "name": "Fat Butcher",
        "order": parse_order("SMGD"),
        "unshaded": "Casino-man Nicholas di Costanzo draws US heat: Close 1 Casino or Aid -8.",
        "shaded": "Mob enforcer: Syndicate free Ambushes and opens 1 closed Casino."
    },
    42: {
        "name": "Llano",
        "order": parse_order("SMGD"),
        "unshaded": "Slums to arms: Place a 26July Base and any Guerrilla in a City.",
        "shaded": "Urban poor indifferent, eager for work: Select a City. Remove any Opposition there and place an open Casino"
    },
    43: {
        "name": "Mafia Offensive",
        "order": parse_order("SMDG"),
        "unshaded": "Mob helps rebels: 26July or DR executes a free LimOp, treating 1 Syndicate piece as that Faction’s piece.",
        "shaded": "INSURGENT CAPABILITY: Hitmen: Syndicate may Assassinate as if DR, but regardless of Police."
    },
    44: {
        "name": "Rebel Air Force",
        "order": parse_order("SMDG"),
        "unshaded": "Captured aircraft shocks troops: A 26July or DR Guerrilla (Active or not) free Ambushes Government forces. Remove Bases first.",
        "shaded": "Rebels purchase but cannot operate aircraft: Select 26July or DR and transfer 1 die roll of their Resources to Syndicate."
    },
    45: {
        "name": "Anastasia",
        "order": parse_order("SDGM"),
        "unshaded": "Rival muscles into Cuba: Close all Casinos in Havana. Syn Resources -5.",
        "shaded": "Lansky rival whacked: Syndicate Resources +10."
    },
    46: {
        "name": "Sinatra",
        "order": parse_order("SDGM"),
        "unshaded": "Over-priced star: Syndicate Resources -6.",
        "shaded": "Frankie’s show: Place an open Casino in Havana regardless of stacking. Place 1 Cash with Police there."
    },
    47: {
        "name": "Pact of Miami",
        "order": parse_order("SDMG"),
        "unshaded": "Surprise for dictator and rebels: Remove 2 Guerrillas. Govt Ineligible through next card.",
        "shaded": "Agreement causes confusion: 26July and Directorio each lose –3 Resources and are Ineligible through next card."
    },
    48: {
        "name": "Santo Trafficante, Jr",
        "order": parse_order("SDMG"),
        "unshaded": "Feud with Lansky: Syndicate Resources –10. All Syn Guerrillas Active.",
        "shaded": "INSURGENT CAPABILITY: Old-time mobster: Underground Syn block Skim."
    }
}
