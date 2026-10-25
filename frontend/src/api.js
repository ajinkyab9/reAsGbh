// All requests use relative /api paths. The same code works in:
//   - Vite dev   (vite.config.js proxy -> localhost:8000)
//   - Docker     (nginx proxy -> backend:8000)
//   - Vercel     (Services rewrite -> backend service)
// VITE_API_BASE is an escape hatch if the backend is ever hosted separately.
const BASE = import.meta.env.VITE_API_BASE ?? ''

export async function getJSON(path, params = {}) {
  const qs = new URLSearchParams(params).toString()
  const res = await fetch(`${BASE}/api${path}${qs ? `?${qs}` : ''}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}
