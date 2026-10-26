// All requests use relative /api paths. The same code works in:
//   - Vite dev   (vite.config.js proxy -> localhost:8000)
//   - Docker     (nginx proxy -> backend:8000)
//   - Vercel     (Services rewrite -> backend service)
// VITE_API_BASE is an another route if the backend is ever hosted separately.
const BASE = import.meta.env.VITE_API_BASE ?? "";

/** Build an API path with a query string. */
export function apiPath(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  return qs ? `${path}?${qs}` : path;
}

export async function getJSON(path, { signal } = {}) {
  const res = await fetch(`${BASE}/api${path}`, { signal });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}