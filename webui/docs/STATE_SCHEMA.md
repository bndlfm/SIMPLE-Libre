# UI State Schema (Draft)

This schema is designed to be derived from the existing Cuba Libre env without modifying it.

## Envelope
```json
{
  "ts": 0,
  "game": "cubalibre",
  "done": false,
  "phase": 0,
  "current_player": 0,
  "players": [ ... ],
  "tracks": { ... },
  "card": { ... },
  "spaces": [ ... ],
  "legal_actions": { "n": 0, "ones": [0, 1, 2] }
}
```

## Players
```json
{
  "id": 0,
  "name": "GOVT",
  "resources": 15,
  "eligible": true,
  "available_forces": [30, 20],
  "available_bases": 3
}
```

## Tracks
```json
{
  "aid": 15,
  "us_alliance": 0,
  "total_support": 0,
  "opposition_plus_bases": 0,
  "dr_pop_plus_bases": 0,
  "open_casinos": 0,
  "propaganda_cards_played": 0
}
```

## Card
```json
{
  "current": {
    "id": 13,
    "name": "El Che",
    "is_propaganda": false,
    "faction_order": ["M26","GOVT","DR","SYNDICATE"],
    "unshaded": "...",
    "shaded": "..."
  },
  "next": { "id": 27, "name": "Echeverria", "is_propaganda": false }
}
```

## Space
```json
{
  "id": 3,
  "name": "Havana",
  "type": 0,
  "population": 6,
  "econ": 0,
  "adj": [2],
  "alignment": 0,
  "support_active": false,
  "terror": 0,
  "sabotage": false,
  "controlled_by": 1,
  "pieces": {
    "govt": {"troops": 6, "police": 4, "base": 0},
    "m26":  {"underground": 0, "active": 0, "base": 0},
    "dr":   {"underground": 0, "active": 0, "base": 0},
    "syn":  {"underground": 0, "active": 0, "casino_open": 0, "casino_closed": 0},
    "cash": {"govt": 0, "m26": 0, "dr": 0, "syn": 0}
  }
}
```

## Legal actions
For UI efficiency, transmit legal actions as a sparse list of indices (`ones`).
