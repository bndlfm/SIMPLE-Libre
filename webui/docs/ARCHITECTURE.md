# Web UI Architecture (Draft)

## 1) Key requirements
- Real-time, human-friendly visualization of Cuba Libre state
- Clickable / selectable map spaces (and later: piece-level selection)
- Card/deck display (current card + peeked next card)
- Available forces boxes / track markers (Aid, US Alliance, Resources, etc.)
- Works in 2 modes:
  - Interactive play (human sends actions)
  - Spectator (observe env updates from training)

## 2) Proposed split

### Frontend (React)
- Renders current state snapshot
- Shows `legal_actions` and phase context to drive UI affordances
- Emits user intents as `action` integers compatible with env `action_space`

### Backend (FastAPI)
- Owns an instance of `CubaLibreEnv`
- Converts env internal structures to a stable JSON schema for the UI
- Provides:
  - REST for `state`, `reset`, `step`, `legal_actions`
  - WebSocket channel broadcasting state diffs/snapshots

## 3) Training spectator integration (later)
Because training currently runs without UI hooks, there are multiple non-invasive options:

- Option A (recommended): **sidecar state publisher**
  - Training process writes periodic JSON snapshots (or action logs) to a shared file/pipe.
  - WebUI backend tails and rebroadcasts via WS.

- Option B: **in-process hook**
  - Training imports a lightweight publisher module and pushes state updates to backend WS.
  - Requires minimal changes to training entrypoints.

- Option C: **replay from logs**
  - Save seeds + action traces; UI replays deterministically.

## 4) Map rendering approach
- Use an SVG map layer with 13 named space hitboxes.
- Overlay counts for each piece slot and markers (terror, sabotage, cash, control).
- Later: replace with a traced board map image and calibrated hit areas.
