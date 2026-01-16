import random
import numpy as np
from .data import EVENT_DECK_DATA

# Constants
FACTIONS = ["GOVT", "M26", "DR", "SYNDICATE"]

FACTION_CASH_PIECES = {
    0: [0, 1],  # Govt Troops, Police
    1: [2, 3],  # M26 UG/Active
    2: [5, 6],  # DR UG/Active
    3: [8, 9],  # Syndicate UG/Active
}

TERRAIN_MAP = {
    "city": 0, 
    "forest": 1, 
    "grass": 2, 
    "mountain": 3, 
    "econ": 4
}

class Faction():
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.resources = 0
        self.eligible = True

        # --- STRICT PIECE LIMITS ---
        if name == "GOVT":
            self.available_forces = [30, 20] # Troops, Police
            self.available_bases = 3
        elif name == "SYNDICATE":
            self.available_forces = [20]     # Guerrillas
            self.available_bases = 6         # Casinos
        else:
            self.available_forces = [15]     # Guerrillas
            self.available_bases = 10        # Bases

        # Victory Tracking
        self.total_support = 0 
        self.bases_placed = 0  
        self.opposition_bases = 0 
        self.control_bases = 0 
        self.open_casinos = 0 
        self.cash = 0 

class Card():
    def __init__(self, id, name, faction_order, text_unshaded, text_shaded):
        self.id = id
        self.name = name
        self.faction_order = faction_order
        self.text_unshaded = text_unshaded
        self.text_shaded = text_shaded
        self.is_propaganda = False

class PropagandaCard(Card):
    def __init__(self, id):
        super().__init__(id, "Propaganda!", [], "Victory Check", "Reset")
        self.is_propaganda = True

class Deck():
    def __init__(self):
        self.cards = []
        self.create()

    def create(self):
        # 1. Create all 48 Event Cards from Data
        events = []
        for id, data in EVENT_DECK_DATA.items():
            events.append(Card(
                id, 
                data['name'], 
                data['order'], 
                data['unshaded'], 
                data['shaded']
            ))
        random.shuffle(events)
        
        # 2. Split into 4 piles
        # 48 cards / 4 piles = 12 cards per pile
        piles = [events[i:i + 12] for i in range(0, len(events), 12)]
        
        # 3. Add 1 Propaganda Card to each pile and shuffle
        self.cards = []
        for i, pile in enumerate(piles):
            pile.append(PropagandaCard(100 + i)) # IDs 100-103
            random.shuffle(pile)
            self.cards.extend(pile) # Stack on top

    def draw(self):
        if len(self.cards) > 0:
            return self.cards.pop()
        return None
    
    def peek(self):
        """View the next card without removing it (board game 'look ahead' mechanic)."""
        if len(self.cards) > 0:
            return self.cards[-1]
        return None

class Space():
    def __init__(self, id, name, type_str, pop, econ, adjacencies):
        self.id = id
        self.name = name
        self.type = TERRAIN_MAP.get(type_str.lower(), 2) 
        self.population = pop
        self.econ_value = econ
        self.adj_ids = adjacencies
        
        # Dynamic State
        self.alignment = 0 
        self.support_active = False 
        self.terror = 0
        self.sabotage = False
        
        # 11 Slots: 0-1(Govt), 2-4(M26), 5-7(DR), 8-10(Syn)
        self.pieces = np.zeros(11, dtype=int)
        self.closed_casinos = 0
        # Cash markers are tracked per holder piece index; cash is derived per faction.
        self.cash_holders = np.zeros(11, dtype=int)
        # Cash ownership per holder index; -1 means infer from default holder faction mapping.
        self.cash_owner_by_holder = np.full(11, -1, dtype=int)
        self.cash = np.zeros(4, dtype=int)
        self.govt_bases = 0 
        
        # Control Status: 0=None, 1=Govt, 2=M26, 3=DR, 4=Syn
        self.controlled_by = 0

    def update_control(self):
        """
        1.3.2 Control Rules
        """
        govt_cubes = self.pieces[0] + self.pieces[1]
        
        m26_pieces = self.pieces[2] + self.pieces[3] + self.pieces[4]
        dr_pieces  = self.pieces[5] + self.pieces[6] + self.pieces[7]
        syn_pieces = self.pieces[8] + self.pieces[9] + self.pieces[10]
        
        total_insurgents = m26_pieces + dr_pieces + syn_pieces
        
        # Check Govt Control
        if govt_cubes > total_insurgents:
            self.controlled_by = 1 
            return

        # Check M26 Control
        others_m26 = govt_cubes + dr_pieces + syn_pieces
        if m26_pieces > others_m26:
            self.controlled_by = 2 
            return
            
        # Check DR Control
        others_dr = govt_cubes + m26_pieces + syn_pieces
        if dr_pieces > others_dr:
            self.controlled_by = 3 
            return
            
        # Check Syn Control
        others_syn = govt_cubes + m26_pieces + dr_pieces
        if syn_pieces > others_syn:
            self.controlled_by = 4 
            return
            
        self.controlled_by = 0 

    def refresh_cash_counts(self):
        self.cash[:] = 0
        # Default behavior: cash holders count toward their faction's cash.
        # Extended behavior: some effects place cash owned by one faction with another faction's holder.
        for idx in range(len(self.cash_holders)):
            count = int(self.cash_holders[idx])
            if count <= 0:
                continue
            owner = int(self.cash_owner_by_holder[idx])
            if owner < 0:
                # Infer ownership from default holder mappings.
                inferred = None
                for faction_idx, piece_indices in FACTION_CASH_PIECES.items():
                    if idx in piece_indices:
                        inferred = int(faction_idx)
                        break
                if inferred is None:
                    continue
                owner = inferred
            if 0 <= owner < len(self.cash):
                self.cash[owner] += count

    @property
    def symbol(self):
        if self.type == 4:
            return f"[{self.name}]"
        return f"{self.name}"

class Board():
    def __init__(self):
        self.spaces = []
        self.create_map()
        self.total_spaces = len(self.spaces)

    def create_map(self):
        self.spaces = [
            ########################
            #     Terrain Types:   #
            # 0: CITY              #
            # 1: PROVINCE_FOREST   #
            # 2: PROVINCE_GRASS    #
            # 3: PROVINCE_MOUNTAIN #
            # 4: ECON_CENTER       #
            ########################
            #     ID,   NAME,               TERRAIN,    POP,    ECON,   ADJACENT
            Space(0,    "Pinar Del Rio",    "forest",   1,      0,      [ 1, 2          ]),
            Space(1,    "Cigar EC",         "econ",     0,      3,      [ 0, 2          ]),
            Space(2,    "La Habana",        "grass",    1,      0,      [ 0, 1, 3, 4    ]),
            Space(3,    "Havana",           "city",     6,      0,      [ 2,            ]),
            Space(4,    "Matanzas",         "grass",    1,      0,      [ 2, 5          ]),
            Space(5,    "Las Villas",       "mountain", 2,      0,      [ 4, 6, 7       ]),
            Space(6,    "Textile EC",       "econ",     0,      3,      [ 5, 7          ]),
            Space(7,    "Camaguey",         "forest",   1,      0,      [ 5, 6, 8, 9    ]),
            Space(8,    "Camaguey City",    "city",     1,      0,      [ 7,            ]),
            Space(9,    "Oriente",          "forest",   2,      1,      [ 7, 10, 11     ]),
            Space(10,   "Sugar Cane EC",    "econ",     0,      2,      [ 9, 11         ]),
            Space(11,   "Sierra Maestra",   "mountain", 1,      0,      [ 9, 10, 12     ]),
            Space(12,   "Santiago De Cuba", "city",     1,      0,      [ 11            ])
        ]

    def get_piece_index(self, faction_idx, piece_type):
        if faction_idx == 0: 
            return piece_type # Govt

        # Insurgents: M26(1)->2, DR(2)->5, Syn(3)->8
        offset = 2 + ((faction_idx - 1) * 3)
        return offset + piece_type

    def add_piece(self, space_id, faction_idx, piece_type):
        idx = self.get_piece_index(faction_idx, piece_type)
        self.spaces[space_id].pieces[idx] += 1
        self.spaces[space_id].update_control()

    def remove_piece(self, space_id, faction_idx, piece_type):
        idx = self.get_piece_index(faction_idx, piece_type)
        if self.spaces[space_id].pieces[idx] > 0:
             self.spaces[space_id].pieces[idx] -= 1
             sp = self.spaces[space_id]
             if piece_type == 2 and faction_idx in [1, 2]:
                 env = getattr(self, "env", None)
                 if env is not None:
                     env._record_pact_base_removal(int(faction_idx))
             if hasattr(sp, "cash_holders"):
                 if sp.pieces[idx] == 0 and int(sp.cash_holders[idx]) > 0:
                     cash_to_move = int(sp.cash_holders[idx])
                     env = getattr(self, "env", None)
                     if env is not None:
                         env._queue_cash_transfer(space_id, faction_idx, idx, cash_to_move)
                     else:
                         sp.cash_holders[idx] = 0
                     sp.refresh_cash_counts()
             self.spaces[space_id].update_control()
             return True
        return False
