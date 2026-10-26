import { useEffect, useState } from 'react'
import { getJSON } from './api'

/*this fetches api path and refetches that on changes. supports additional fetching
preservres previoud sata while loading and aborts outdated requests to prevent stale responses */
export function useApi(path) {
  const [result, setResult] = useState({ path: null, data: null, error: null })

  useEffect(() => {
    if (!path) return
    const controller = new AbortController()
    getJSON(path, { signal: controller.signal })
      .then((data) => setResult({ path, data, error: null }))
      .catch((error) => {
        if (error.name !== 'AbortError') setResult({ path, data: null, error })
      })
    return () => controller.abort()
  }, [path])

  return { ...result, loading: Boolean(path) && result.path !== path }
}