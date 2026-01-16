# Cuba Libre (2018) Rules Spec for SIMPLE-Libre

This document is the acceptance target for making `app/environments/cubalibre/envs/` a **1:1 rules engine** for **Cuba Libre (2018)**.

Scope for now:
- Full campaign setup (2018).
- Human vs RL agent (no COIN Bots).
- A single RL policy must be able to play **any faction**, including controlling multiple factions in the same game.

Non-goals (for now):
- Scenarios (but design must allow adding scenario setup later).

---

## 1) Authoritative state model (must exist in env)

### 1.1 Factions
- Government (GOVT)
- 26 July Movement (M26)
- Directorio (DR)
- Syndicate (SYNDICATE)

Each faction needs:
- Resources
- Piece pools (available forces, available bases)
- Eligibility state (eligible/ineligible)
- Victory-relevant totals (derived)

### 1.2 Map spaces
Each space must encode, at minimum:
- Type: City / Province / Mountain / Economic (and any 2018 distinctions)
- Population/economic values
- Alignment state (support/opposition/neutral with active/passive where applicable)
- Terror marker
- Sabotage marker
- Cash markers (per-faction ownership and per-piece holders)
- Pieces (Govt troops/police/bases, insurgent guerrillas active/underground + bases/casinos)
- Control (computed per COIN rules)

### 1.3 Tracks & global markers (2018)
The 2018 campaign uses global tracks/markers that must be represented explicitly (not approximated via Resources):
- US Alliance (Firm/Reluctant/Embargoed; exact model per 2018)
- Aid (and any derived funding)
- Opposition / Support totals (derived from space alignment)
- Any other campaign-level markers required by Propaganda and victory checks

(Implementation note: keep these as explicit numeric fields on env, not inferred.)

### 1.4 Capabilities / Momentum
- Event capabilities must be represented with:
  - Identity
  - Duration (permanent / until next Propaganda / until end of campaign)
- Expiration must be handled in Propaganda cleanup.

### 1.5 Cash markers & transfers (2018)
Cash markers are faction-owned and must be tracked explicitly per space. Ownership does not change when the marker moves.
Rules requirements to encode:
- A cash marker is held by a specific eligible piece in the same space (Govt cubes; insurgent guerrillas, not bases/casinos).
- When cash transfers between factions (e.g., Meyer Lansky), only the holder changes; ownership stays with the original faction.
- If a cash-holding piece is removed and no piece of that holder type remains, play proceeds to an explicit decision phase:
  - Move the cash to another eligible piece in the space (same faction if possible, otherwise any faction with eligible pieces),
  - or remove the cash marker.
- Cash markers are removed/converted during Propaganda cash deposits per the rules.

---

## 2) Sequence of play (2018)

### 2.1 Card flow
- Draw next card.
- If Event card:
  - Determine eligible order printed on card.
  - Up to two factions act, following COIN eligibility/ineligibility rules.
- If Propaganda card:
  - Execute full Propaganda round procedure.
  - Check victory.
  - Reset eligibility appropriately.

### 2.2 Eligibility & acting
Must match 2018 COIN rules:
- Determine 1st eligible faction (topmost in order that is eligible).
- 1st eligible chooses: Pass, Event, or Op+possible SA.
- Then 2nd eligible chooses: Pass, Event, or Limited Op (and SA restrictions) depending on what 1st did.
- Update eligibility/ineligibility after each faction acts.

(Implementation requirement: eligibility rules must be explicit state machine logic, not approximated by counters.)

---

## 3) Action model requirements (for RL and human play)

### 3.1 No hidden heuristic choices
Any rules-required choice must be expressed as an explicit decision phase:
- Choosing Event vs Ops vs Pass
- Choosing event side (unshaded/shaded)
- Choosing operation type
- Choosing spaces/targets
- Choosing number of pieces to move/remove (when not forced)
- Choosing special activity (or skipping)

### 3.2 Phase/state machine
The environment must expose a multi-step decision process where each `step()` consumes exactly one decision.
Phases should minimally cover:
- Choose main action
- Choose event side
- Choose event targets (if required)
- Choose op action
- Choose op targets/parameters
- Choose special activity and its targets/parameters
- Resolve + advance to next decision-maker

### 3.3 Faction-agnostic policy support
Observation must include:
- Current acting faction
- Current phase
- Current card info
So a single policy network can learn to play any faction.

Observation header layout (current implementation; length 14):
- 0: phase
- 1: current player index
- 2: factions acted this card
- 3: US Alliance (0=Firm, 1=Reluctant, 2=Embargoed)
- 4: current card id
- 5: pending main (-1 none, 0 event, 1 ops)
- 6: current player resources
- 7: deck empty flag
- 8: current player eligible flag
- 9: Aid track
- 10: Total Support (derived)
- 11: Opposition + Bases (derived)
- 12: DR Pop + Bases (derived)
- 13: Open Casinos (derived)

---

## 4) Operations (2018)

For each faction, implement operations and special activities faithfully:
- Govt: Train, Garrison, Sweep, Assault, Transport, Air Strike (+ any 2018 specifics)
- M26: Rally, March, Attack, Terror, Ambush, Kidnap
- DR: Rally, March, Attack, Terror, Assassinate
- Syndicate: Rally, March, Attack, Terror, Bribe, Construct

Each operation must:
- Enforce legality (space restrictions, prerequisites, resources, etc.)
- Apply correct costs
- Apply correct piece movement/activation/reveal rules
- Apply correct control updates

---

## 5) Events (cards 1–48)

For each event side:
- Implement 2018 text exactly.
- Encode required player choices as phases.
- Track lasting effects as capabilities with correct durations.

Testing requirement:
- Each card must have at least one unit test (or a regression fixture) verifying key state deltas.

---

## 6) Propaganda round (2018)

Must implement full Propaganda sequence, including:
- Resource / Aid adjustments
- Redeploy / Casualties / any resets
- Eligibility reset
- Capability duration cleanup
- Victory check with correct thresholds

---

## 7) Scenario support (later)

Scenario support should be implemented as:
- A scenario data object describing initial map, tracks, and deck configuration.
- A scenario initializer that configures env state.

Core rules engine must not be duplicated per scenario.
