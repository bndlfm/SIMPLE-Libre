import React, { useEffect, useMemo, useRef, useState } from 'react'
import { apiGet, apiPost, getBaseUrl, setBaseUrl } from './api.js'
import { SPACE_HITBOXES } from './mapLayout.js'
import ModelSelector from './ModelSelector'
import { SpacePieces } from './PieceRender.jsx'


function factionNameFromId(id) {
  if (id === 0) return 'GOVT'
  if (id === 1) return 'M26'
  if (id === 2) return 'DR'
  if (id === 3) return 'SYNDICATE'
  return String(id)
}

function controlledByName(id) {
  if (id === 0) return 'None'
  if (id === 1) return 'GOVT'
  if (id === 2) return 'M26'
  if (id === 3) return 'DR'
  if (id === 4) return 'SYNDICATE'
  return String(id)
}

function phaseName(phase) {
  const map = {
    0: 'CHOOSE_MAIN',
    1: 'CHOOSE_EVENT_SIDE',
    2: 'CHOOSE_OP_ACTION',
    3: 'CHOOSE_LIMITED_OP_ACTION',
    4: 'CHOOSE_SPECIAL_ACTIVITY',
    5: 'CHOOSE_TARGET_SPACE',
    6: 'CHOOSE_TARGET_FACTION',
    7: 'CHOOSE_EVENT_OPTION',
    8: 'CHOOSE_TARGET_PIECE',
    9: 'PROPAGANDA_REDEPLOY_MENU'
  }
  return map[phase] || String(phase)
}

function piecesSummary(space) {
  const p = space.pieces_raw || []
  const govt = `GOVT T:${p[0] || 0} P:${p[1] || 0}`
  const m26 = `M26 U:${p[2] || 0} A:${p[3] || 0} B:${p[4] || 0}`
  const dr = `DR U:${p[5] || 0} A:${p[6] || 0} B:${p[7] || 0}`
  const syn = `SYN U:${p[8] || 0} A:${p[9] || 0} C:${p[10] || 0} (closed:${space.closed_casinos || 0})`
  return `${govt} | ${m26} | ${dr} | ${syn}`
}

function ControlsPanel({ state, onStep }) {
  const [val, setVal] = useState('')
  if (!state) return null

  const { phase, legal_actions, action_ranges, pending } = state
  const legalSet = new Set(legal_actions.ones)

  // PHASE 0: CHOOSE_MAIN
  if (phase === 0) {
    const base = action_ranges.main.base
    // 0=Pass, 1=Event, 2=Ops
    const actions = [
      { label: 'Pass', id: base + 0 },
      { label: 'Event', id: base + 1 },
      { label: 'Ops', id: base + 2 }
    ]
    return (
      <div className="row">
        {actions.map((a) => (
          <button
            key={a.id}
            disabled={!legalSet.has(a.id)}
            onClick={() => onStep(a.id)}
          >
            {a.label}
          </button>
        ))}
      </div>
    )
  }

  // PHASE 1: CHOOSE_EVENT_SIDE
  if (phase === 1) {
    const base = action_ranges.event_side.base
    const actions = [
      { label: 'Unshaded', id: base + 0 },
      { label: 'Shaded', id: base + 1 }
    ]
    return (
      <div className="row">
        {actions.map((a) => (
          <button
            key={a.id}
            disabled={!legalSet.has(a.id)}
            onClick={() => onStep(a.id)}
          >
            {a.label}
          </button>
        ))}
      </div>
    )
  }

  // PHASE 6: CHOOSE_TARGET_FACTION
  if (phase === 6) {
    const base = action_ranges.target_faction.base
    const allowed = pending?.faction?.allowed || [0, 1, 2, 3]
    return (
      <div className="col">
        <div className="small">Select Faction for <b>{pending?.faction?.event || 'Event'}</b>:</div>
        <div className="row" style={{ marginTop: 5 }}>
          {allowed.map((fId) => {
            const actId = base + fId
            return (
              <button
                key={actId}
                disabled={!legalSet.has(actId)}
                onClick={() => onStep(actId)}
              >
                {factionNameFromId(fId)}
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  // PHASE 7: CHOOSE_EVENT_OPTION
  if (phase === 7) {
    const base = action_ranges.event_option.base
    const allowed = pending?.option?.allowed || []
    return (
      <div className="col">
        <div className="small">Choose Option for <b>{pending?.option?.event || 'Event'}</b>:</div>
        <div className="row" style={{ marginTop: 5 }}>
          {allowed.map((optIdx) => {
            const actId = base + optIdx
            return (
              <button
                key={actId}
                disabled={!legalSet.has(actId)}
                onClick={() => onStep(actId)}
              >
                Option {optIdx}
              </button>
            )
          })}
        </div>
      </div>
    )
  }

  // PHASE 2, 3, 4: OPS / LIMOPS / SPECIAL ACTIVITY
  if (phase === 2 || phase === 3 || phase === 4) {
    return <OpsPanel state={state} onStep={onStep} />
  }

  // Fallback for other phases - still allow raw input for debugging
  return (
    <div className="col">
      <div className="small">Raw Action Input (Phase {phaseName(phase)})</div>
      <div className="row">
        <input
          value={val}
          onChange={e => setVal(e.target.value)}
          placeholder="Action ID"
        />
        <button onClick={() => onStep(Number(val))}>Send</button>
      </div>
    </div>
  )
}

const OPS = {
  // GOVT
  0: "Train Force", 1: "Train Base", 2: "Garrison", 3: "Sweep",
  4: "Assault", 5: "Transport", 6: "Air Strike",
  // M26
  7: "Rally", 8: "March", 9: "Attack", 10: "Terror",
  15: "Ambush", 16: "Kidnap",
  // DR
  11: "Rally", 12: "March", 13: "Attack", 14: "Terror",
  17: "Assassinate",
  // Syndicate
  18: "Rally", 19: "March", 20: "Attack", 21: "Terror",
  22: "Bribe", 23: "Construct",
  // Shared
  24: "Event", 25: "Pass"
}

function OpsPanel({ state, onStep }) {
  const [selectedOp, setSelectedOp] = useState(null)

  const { phase, legal_actions, action_ranges, spaces } = state
  const legalSet = new Set(legal_actions.ones)

  // Determine base offset
  let base = 0
  let count = 0
  if (phase === 3) {
    // Limited Ops
    base = action_ranges.limited_ops.base
    count = action_ranges.limited_ops.count
  } else {
    // Ops (2) or Special Activity (4) - both use main Ops range
    base = action_ranges.ops.base
    count = action_ranges.ops.count
  }

  // Parse valid Ops and Spaces
  const validOps = useMemo(() => {
    const map = new Map() // opId -> [spaceIds]

    legal_actions.ones.forEach(id => {
      if (id >= base && id < base + count) {
        const rel = id - base
        const opId = Math.floor(rel / 13)
        const spaceId = rel % 13

        if (!map.has(opId)) map.set(opId, [])
        map.get(opId).push(spaceId)
      }
    })
    return map
  }, [legal_actions, base, count])

  // If selected OP is no longer valid (e.g. after update), clear it
  if (selectedOp !== null && !validOps.has(selectedOp)) {
    // We can't set state during render, but we can treat it as null
    // Effect will handle cleanup if needed, but for render just show op list
  }

  const opIds = Array.from(validOps.keys()).sort((a, b) => a - b)

  if (selectedOp === null || !validOps.has(selectedOp)) {
    return (
      <div className="col">
        <div className="small">Select Operation:</div>
        <div className="row" style={{ flexWrap: 'wrap', gap: 4 }}>
          {opIds.map(opId => (
            <button key={opId} onClick={() => setSelectedOp(opId)}>
              {OPS[opId] || `Op ${opId}`}
            </button>
          ))}
        </div>
      </div>
    )
  }

  const spaceIds = validOps.get(selectedOp).sort((a, b) => a - b)
  const opName = OPS[selectedOp] || `Op ${selectedOp}`

  return (
    <div className="col">
      <div className="row">
        <button className="secondary" onClick={() => setSelectedOp(null)}>← Back</button>
        <div className="small" style={{ alignSelf: 'center', marginLeft: 10 }}>
          Target for <b>{opName}</b>:
        </div>
      </div>
      <div className="row" style={{ flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
        {spaceIds.map(sId => {
          const sp = spaces.find(s => s.id === sId)
          const name = sp ? sp.name : `Space ${sId}`
          const actId = base + (selectedOp * 13) + sId
          return (
            <button key={sId} onClick={() => onStep(actId)}>
              {name}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function App() {
  const [baseUrl, setBaseUrlState] = useState(getBaseUrl())
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)
  const [selectedSpaceId, setSelectedSpaceId] = useState(null)
  const wsRef = useRef(null)
  // Faction roles: local UI state, synced with server
  const [factionRoles, setFactionRoles] = useState({ 0: 'human', 1: 'ai', 2: 'ai', 3: 'ai' })
  // Scenario
  const [scenario, setScenario] = useState('standard')
  // Model
  // Model
  // const [modelPath, setModelPath] = useState('zoo/cubalibre/best_model.zip')
  // const [modelDevice, setModelDevice] = useState('')
  // Spectator
  const [spectatorTickMs, setSpectatorTickMs] = useState(500)
  // Training watch
  const [trainingPath, setTrainingPath] = useState('')
  const [trainingPoll, setTrainingPoll] = useState(1)
  const [trainingState, setTrainingState] = useState(null)

  const meta = state?.meta || {}
  const modelInfo = meta.model || {}
  const spectatorInfo = meta.spectator || {}
  const serverRoles = meta.faction_roles || {}
  const trainingInfo = trainingState?.data ?? meta.training
  const trainingError = trainingState?.error ?? meta.training_error
  const trainingUpdatedAt = trainingState?.updated_at ?? meta.training_updated_at

  function toggleFactionRole(id) {
    setFactionRoles((prev) => ({
      ...prev,
      [id]: prev[id] === 'human' ? 'ai' : 'human'
    }))
  }

  function factionRolesPayload() {
    return Object.fromEntries(
      Object.entries(factionRoles).map(([k, v]) => [String(k), v])
    )
  }

  function formatTimestamp(ts) {
    if (!ts) return '\u2014'
    try {
      return new Date(ts).toLocaleString()
    } catch {
      return ts
    }
  }

  const humanCount = Object.values(factionRoles).filter((r) => r === 'human').length
  const aiCount = 4 - humanCount
  const configLabel = `${humanCount}H / ${aiCount}AI`

  // ---- API actions ----



  async function applyFactionRoles() {
    setError(null)
    try {
      const res = await apiPost('/faction_roles', { faction_roles: factionRolesPayload() })
      if (res?.meta) setState(res)
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  async function startSpectator() {
    setError(null)
    try {
      await apiPost('/spectator/start', { tick_ms: spectatorTickMs, deterministic: false, auto_reset: true })
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  async function stopSpectator() {
    setError(null)
    try {
      await apiPost('/spectator/stop')
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  async function watchTraining() {
    setError(null)
    try {
      const res = await apiPost('/training/watch', {
        path: trainingPath || null,
        poll_seconds: Number(trainingPoll) || 1
      })
      setTrainingState(res.status)
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  const mapImageUrl = useMemo(() => {
    return `${baseUrl}/assets/CubaLibreMap-FINAL-120.jpg`
  }, [baseUrl])

  const targetSpaceBase = state?.action_ranges?.target_space?.base ?? null

  const selectedSpace = useMemo(() => {
    if (!state?.spaces) return null
    return state.spaces.find((s) => s.id === selectedSpaceId) || null
  }, [state, selectedSpaceId])

  const isChoosingTargetSpace = state?.phase === 5

  async function refresh() {
    setError(null)
    try {
      const s = await apiGet('/state')
      setState(s)
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  async function reset() {
    setError(null)
    try {
      const s = await apiPost('/reset', {
        faction_roles: factionRolesPayload(),
        scenario: scenario
      })
      setState(s)
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  async function step(action) {
    setError(null)
    try {
      const res = await apiPost('/step', { action })
      setState(res.state)
    } catch (e) {
      setError(String(e?.message || e))
    }
  }

  function connectWs() {
    try {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      const url = new URL(baseUrl)
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      url.pathname = '/ws'
      const ws = new WebSocket(url.toString())
      wsRef.current = ws

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data)
          if (msg.type === 'state') {
            setState(msg.payload)
          }
          if (msg.type === 'training') {
            setTrainingState(msg.payload)
          }
        } catch {
          // ignore
        }
      }

      ws.onerror = () => {
        // fall back to REST
      }

      ws.onclose = () => {
        // ignore
      }
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    refresh()
    connectWs()
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Determine if it's currently a human player's turn
  const isHumanTurn = state ? factionRoles[state.current_player] === 'human' : false

  // Determine winner if done
  let winnerText = ""
  if (state && state.done) {
    const sorted = [...state.players].sort((a, b) => b.points - a.points)
    const winner = sorted[0]
    winnerText = `${winner.name} wins!`
    if (sorted[0].points === sorted[1].points) winnerText = "Draw!"
  }

  return (
    <div className="container">
      {state && state.done && (
        <div style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.85)', zIndex: 9999,
          display: 'flex', alignItems: 'center', justifyContent: 'center'
        }}>
          <div style={{ backgroundColor: '#222', padding: 40, borderRadius: 8, textAlign: 'center', border: '1px solid #444', maxWidth: 600, width: '100%' }}>
            <h1 style={{ color: '#fff', marginBottom: 10 }}>GAME OVER</h1>
            <h2 style={{ color: '#4CAF50', marginBottom: 30 }}>{winnerText}</h2>

            <table style={{ margin: '0 auto 30px auto', borderCollapse: 'collapse', width: '100%' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #555' }}>
                  <th style={{ padding: 10, textAlign: 'left' }}>Faction</th>
                  <th style={{ padding: 10, textAlign: 'right' }}>Score</th>
                  <th style={{ padding: 10, textAlign: 'right' }}>Resources</th>
                </tr>
              </thead>
              <tbody>
                {[...state.players].sort((a, b) => b.points - a.points).map(p => (
                  <tr key={p.id}>
                    <td style={{ padding: 8, textAlign: 'left' }}>{p.name}</td>
                    <td style={{ padding: 8, textAlign: 'right', fontWeight: 'bold', fontSize: '1.2em' }}>{p.points}</td>
                    <td style={{ padding: 8, textAlign: 'right' }}>{p.resources}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <button
              onClick={() => {
                reset()
                // Also close modal locally if needed, but reset should clear state.done
              }}
              style={{ fontSize: 18, padding: '12px 24px', backgroundColor: '#2196F3', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}
            >
              Play Again
            </button>
          </div>
        </div>
      )}
      <div className="panel">
        <h2>Connection</h2>
        <div className="row">
          <label>Backend</label>
          <input
            value={baseUrl}
            onChange={(e) => setBaseUrlState(e.target.value)}
            style={{ width: 240 }}
          />
          <button
            onClick={() => {
              setBaseUrl(baseUrl)
              connectWs()
              refresh()
            }}
          >
            Save
          </button>
        </div>
        {error ? <pre style={{ color: '#e44' }}>{error}</pre> : <div className="small">WS auto-connect; REST fallback.</div>}

        <h2 style={{ marginTop: 16 }}>Faction Roles ({configLabel})</h2>
        <div className="col">
          <div className="row" style={{ flexWrap: 'wrap', gap: 6 }}>
            {[0, 1, 2, 3].map((fId) => (
              <button
                key={fId}
                onClick={() => toggleFactionRole(fId)}
                style={{
                  background: factionRoles[fId] === 'human' ? '#4a9' : '#68b',
                  color: '#fff',
                  minWidth: 90
                }}
              >
                {factionNameFromId(fId)}: {factionRoles[fId] === 'human' ? 'Human' : 'AI'}
              </button>
            ))}
          </div>
          <div className="row" style={{ marginTop: 6 }}>
            <button onClick={applyFactionRoles}>Apply Roles</button>
            <div className="row" style={{ marginLeft: 10, background: '#333', padding: '2px 8px', borderRadius: 4 }}>
              <label style={{ marginRight: 6, fontSize: '0.8em' }}>Scenario:</label>
              <select
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                style={{ background: '#222', color: '#fff', border: '1px solid #555', fontSize: '0.8em' }}
              >
                <option value="standard">Standard Campaign</option>
                <option value="short">Short Game (8 fewer events)</option>
              </select>
            </div>
            <button onClick={reset} style={{ marginLeft: 10 }}>New Game</button>
            <button onClick={refresh}>Refresh</button>
          </div>
          {Object.keys(serverRoles).length > 0 && (
            <div className="small" style={{ marginTop: 4 }}>
              Server: {[0, 1, 2, 3].map((i) => `${factionNameFromId(i)}=${serverRoles[String(i)] || '?'}`).join(' | ')}
            </div>
          )}
        </div>

        <h2 style={{ marginTop: 16 }}>Controls</h2>
        {spectatorInfo.running ? (
          <div className="small">Spectator mode active. Controls disabled.</div>
        ) : isHumanTurn ? (
          <ControlsPanel state={state} onStep={step} />
        ) : state ? (
          <div className="small">Waiting for AI turn...</div>
        ) : null}

        <h2 style={{ marginTop: 16 }}>Model</h2>
        <ModelSelector modelInfo={modelInfo} onReload={refresh} />

        <h2 style={{ marginTop: 16 }}>Spectator (AI vs AI)</h2>
        <div className="col">
          <div className="row">
            <label>Speed (ms)</label>
            <input
              type="number"
              min="50"
              max="10000"
              step="50"
              value={spectatorTickMs}
              onChange={(e) => setSpectatorTickMs(Number(e.target.value) || 500)}
              style={{ width: 90 }}
            />
            {spectatorInfo.running ? (
              <button onClick={stopSpectator} style={{ background: '#c44', color: '#fff' }}>Stop</button>
            ) : (
              <button onClick={startSpectator} style={{ background: '#4a4', color: '#fff' }}>Start</button>
            )}
          </div>
          <div className="small" style={{ marginTop: 4 }}>
            {spectatorInfo.running ? `Running @ ${spectatorInfo.tick_ms}ms/step` : 'Stopped'}
          </div>
        </div>

        <h2 style={{ marginTop: 16 }}>Status</h2>
        <div className="small">
          Last Action: {meta.last_action ?? '\u2014'} by {meta.last_actor != null ? factionNameFromId(meta.last_actor) : '\u2014'}
        </div>
        {meta.ai_steps != null && <div className="small">AI auto-advanced {meta.ai_steps} steps</div>}

        <h2 style={{ marginTop: 16 }}>Training Watch</h2>
        <div className="col">
          <div className="row">
            <input
              value={trainingPath}
              onChange={(e) => setTrainingPath(e.target.value)}
              placeholder="logs/training.jsonl"
              style={{ width: 220 }}
            />
            <input
              type="number"
              min="0.2"
              step="0.1"
              value={trainingPoll}
              onChange={(e) => setTrainingPoll(e.target.value)}
              style={{ width: 60 }}
            />
            <button onClick={watchTraining}>Watch</button>
          </div>
          {trainingError ? <div className="small" style={{ color: '#e44' }}>Error: {trainingError}</div> : null}
          {trainingInfo ? (
            <pre style={{ fontSize: 11 }}>{JSON.stringify(trainingInfo, null, 2)}</pre>
          ) : (
            <div className="small">Updated: {formatTimestamp(trainingUpdatedAt)}</div>
          )}
        </div>
      </div>

      <div className="panel">
        <h2>Map</h2>
        {!state ? (
          <div className="small">No state loaded yet. Press Reset.</div>
        ) : (
          <>
            <div className="small">
              Phase: <b>{phaseName(state.phase)}</b> | Acting: <b>{factionNameFromId(state.current_player)}</b>
            </div>
            <div className="mapStage" style={{ marginTop: 10 }}>
              <img className="mapImg" src={mapImageUrl} alt="Cuba Libre Map" />
              <div className="mapOverlay">
                {state && <SpacePieces board={state.board} />}
                {SPACE_HITBOXES.map((hb) => {
                  const selected = selectedSpaceId === hb.id
                  const style = {
                    left: `${hb.x}%`,
                    top: `${hb.y}%`,
                    width: `${hb.w}%`,
                    height: `${hb.h}%`
                  }

                  return (
                    <div
                      key={hb.id}
                      className={`hitbox ${selected ? 'hitboxSelected' : ''}`}
                      style={style}
                      onClick={() => {
                        if (isChoosingTargetSpace && typeof targetSpaceBase === 'number') {
                          step(targetSpaceBase + hb.id)
                          return
                        }
                        setSelectedSpaceId(hb.id)
                      }}
                      title={hb.name}
                    >
                      <div className="hitboxLabel">{hb.id}: {hb.name}</div>
                      {state.spaces.find(s => s.id === hb.id) ? (
                        <SpacePieces space={state.spaces.find(s => s.id === hb.id)} />
                      ) : null}
                    </div>
                  )
                })}

                <div className="small" style={{ padding: 10 }}>
                  {isChoosingTargetSpace ? (
                    <>
                      Select Space for <b>{state?.pending?.target?.event || state?.pending?.target?.op || 'Action'}</b>
                    </>
                  ) : (
                    <>
                      Click a space to select it.
                      <br />
                      Selected space: <b>{selectedSpace ? selectedSpace.name : 'None'}</b>
                    </>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="panel">
        <h2>Card / Tracks / Legal</h2>
        {!state ? (
          <div className="small">No state.</div>
        ) : (
          <>
            <div className="kv">
              <div>US Alliance</div>
              <div>{state.tracks.us_alliance}</div>
              <div>Aid</div>
              <div>{state.tracks.aid}</div>
              <div>Total Support</div>
              <div>{state.tracks.total_support}</div>
              <div>Opposition + Bases</div>
              <div>{state.tracks.opposition_plus_bases}</div>
              <div>DR Pop + Bases</div>
              <div>{state.tracks.dr_pop_plus_bases}</div>
              <div>Open Casinos</div>
              <div>{state.tracks.open_casinos}</div>
            </div>

            <h2 style={{ marginTop: 16 }}>Players</h2>
            <div className="kv">
              {state.players.map((p) => (
                <React.Fragment key={p.id}>
                  <div>{p.name}</div>
                  <div>
                    Res:{p.resources} | Eligible:{String(p.eligible)}
                  </div>
                </React.Fragment>
              ))}
            </div>

            <h2 style={{ marginTop: 16 }}>Current Card</h2>
            <div className="small">
              {state.card.current ? (
                <>
                  <div>
                    #{state.card.current.id} {state.card.current.name} (prop:{String(state.card.current.is_propaganda)})
                  </div>
                  <div className="small">Order: {state.card.current.faction_order.join(' ')}</div>
                  <pre>{state.card.current.unshaded}</pre>
                  <pre>{state.card.current.shaded}</pre>
                </>
              ) : (
                'None'
              )}
            </div>

            <h2 style={{ marginTop: 16 }}>Next Card</h2>
            <div className="small">
              {state.card.next ? `#${state.card.next.id} ${state.card.next.name}` : 'None'}
            </div>

            <h2 style={{ marginTop: 16 }}>Legal Actions</h2>
            <div className="small">
              Action space: {state.legal_actions.n} | legal: {state.legal_actions.ones.length}
            </div>
            <pre>{JSON.stringify(state.legal_actions.ones.slice(0, 80), null, 2)}</pre>

            {selectedSpace ? (
              <>
                <h2 style={{ marginTop: 16 }}>Selected Space</h2>
                <pre>{JSON.stringify(selectedSpace, null, 2)}</pre>
              </>
            ) : null}
          </>
        )}
      </div>
    </div>
  )
}
