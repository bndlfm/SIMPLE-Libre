import React, { useState, useEffect } from 'react'
import { apiGet, apiPost } from './api'

export default function ModelSelector({ modelInfo, onReload }) {
    const [models, setModels] = useState([])
    const [selectedModel, setSelectedModel] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)

    useEffect(() => {
        fetchModels()
    }, [])

    // If modelInfo updates (e.g. unloaded externally), sync selection
    useEffect(() => {
        if (modelInfo && modelInfo.path) {
            // Try to match path to name if possible, or just set path
            setSelectedModel(modelInfo.path)
        }
    }, [modelInfo])

    async function fetchModels() {
        try {
            const list = await apiGet('/models')
            setModels(list)
            // Default selection
            if (list.length > 0 && !selectedModel) {
                // Prefer 'best_model.zip' if exists
                const best = list.find(m => m.name === 'best_model.zip')
                if (best) setSelectedModel(best.path)
                else setSelectedModel(list[0].path)
            }
        } catch (e) {
            console.error("Failed to fetch models", e)
        }
    }

    async function loadModel() {
        setLoading(true)
        setError(null)
        try {
            await apiPost('/model/load', {
                path: selectedModel,
                algo: 'PPO' // Default, backend detects MaskablePPO
            })
            if (onReload) onReload()
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    async function unloadModel() {
        setLoading(true)
        setError(null)
        try {
            await apiPost('/model/unload')
            if (onReload) onReload()
        } catch (e) {
            setError(e.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="col">
            <div className="small">
                Loaded: <b>{String(modelInfo?.loaded)}</b>
                {modelInfo?.algo ? ` | Algo: ${modelInfo.algo}` : ''}
            </div>

            <div className="row" style={{ marginTop: 6, gap: 4 }}>
                <select
                    value={selectedModel}
                    onChange={e => setSelectedModel(e.target.value)}
                    style={{ maxWidth: 200 }}
                >
                    {models.map(m => (
                        <option key={m.path} value={m.path}>
                            {m.name} ({m.source})
                        </option>
                    ))}
                </select>
                <button onClick={fetchModels} title="Refresh List">↻</button>
            </div>

            <div className="row" style={{ marginTop: 6, gap: 4 }}>
                <button onClick={loadModel} disabled={loading || !selectedModel}>
                    {loading ? '...' : 'Load'}
                </button>
                <button onClick={unloadModel} disabled={loading || !modelInfo?.loaded}>
                    Unload
                </button>
            </div>

            {error && <div className="small" style={{ color: '#e44' }}>{error}</div>}

            <div className="small" style={{ marginTop: 4, color: '#888' }}>
                {modelInfo?.path ? `Path: ${modelInfo.path}` : 'Use "Load" to activate AI model.'}
            </div>
        </div>
    )
}
