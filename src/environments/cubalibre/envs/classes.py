
import random
import numpy as np

# Constants
FACTIONS = ["GOVT", "M26", "DR", "SYNDICATE"]

# Terrain types based on the Legend in your photo
TERRAIN_MAP = {
    "city": 0,
    "forest": 1,
    "grass": 2,
    "mountain": 3,
    "econ": 4
}

ALIGNMENTS = ["NEUTRAL", "GOVT_SUPPORT", "GOVT_OPPOSITION"]

class Faction():
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.resources = 0
        self.eligible = True
        self.passed = False

        # Victory Tracking
        self.total_support = 0 # Govt
        self.bases_placed = 0  # All Insurgents
        self.opposition_bases = 0 # M26
        self.control_bases = 0 # DR
        self.open_casinos = 0 # Syndicate
        self.cash = 0 # Syndicate

class Card():
    def __init__(self, id, name, faction_order):
        self.id = id
        self.name = name
        self.faction_order = faction_order

class Deck():
    def __init__(self):
        self.cards = []
        self.create()

    def create(self):
        # Sample deck creation
        orders = [
            [0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1], [3, 0, 1, 2]
        ]
        for i in range(10):
            order = orders[i % 4]
            self.cards.append(Card(i, f"Event {i}", order))
        random.shuffle(self.cards)

    def draw(self):
        if len(self.cards) > 0:
            return self.cards.pop()
        return None

class Space():
    def __init__(self, id, name, type_idx, pop, econ, adjacencies):
        self.id = id
        self.name = name
        self.type = type_idx # 0: City, 1: Forest, 2: Grass, 3: Mtn
        self.population = pop
        self.econ_value = econ # 1 if contains Economic Center, else 0
        self.adj_ids = adjacencies

        # Dynamic State
        self.alignment = 0 # 0: Neutral, 1: Support, 2: Opposition
        self.support_active = False
        self.terror = 0
        self.sabotage = False

        # Piece Counts: [Govt_Troop, Govt_Police, M26_G, M26_B, DR_G, DR_B, Syn_G, Syn_B]
        self.pieces = np.zeros(8, dtype=int)

    @property
    def total_pieces(self):
        return np.sum(self.pieces)

    @property
    def symbol(self):
        # Helper for render(): Returns "HAV(S)" for Havana Support
        align_char = "N"
        if self.alignment == 1: align_char = "S"
        elif self.alignment == 2: align_char = "O"
        return f"{self.name[:3].upper()}({align_char})"


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

    def add_piece(sel   f, space_id, faction_idx, piece_type):
        # faction_idx   : 0=Govt, 1=M26, 2=DR, 3=Syn
        # piece_type: 0=Troop/Guerrilla, 1=Police/Base
        idx = (faction_idx * 2) + piece_type
        self.spaces[space_id].pieces[idx] += 1

    def remove_piece(self, space_id, faction_idx, piece_type):
        idx = (faction_idx * 2) + piece_type
        if self.spaces[space_id].pieces[idx] > 0:
             self.spaces[space_id].pieces[idx] -= 1
             return True
        return False
