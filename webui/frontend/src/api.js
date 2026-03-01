const DEFAULT_BASE_URL = 'http://localhost:8001'

export function getBaseUrl() {
  const saved = window.localStorage.getItem('simple_webui_base_url')
  return saved || DEFAULT_BASE_URL
}

export function setBaseUrl(url) {
  window.localStorage.setItem('simple_webui_base_url', url)
}

export async function apiGet(path) {
  const res = await fetch(`${getBaseUrl()}${path}`)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`GET ${path} failed: ${res.status} ${text}`)
  }
  return await res.json()
}

export async function apiPost(path, body) {
  const res = await fetch(`${getBaseUrl()}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: body ? JSON.stringify(body) : undefined
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`POST ${path} failed: ${res.status} ${text}`)
  }
  return await res.json()
}
