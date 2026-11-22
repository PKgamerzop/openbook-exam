import { useEffect, useState } from 'react'

export async function api<T>(
  path: string,
  method = 'GET',
  data?: unknown,
): Promise<T> {
  const response = await fetch('/api' + path, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-OpenBook-Request': '1' },
    body: data === undefined ? undefined : JSON.stringify(data),
  })
  if (!response.ok) {
    if (response.status === 401 && path !== '/login' && path !== '/me') {
      window.dispatchEvent(new Event('openbook-session-expired'))
    }
    const problem = await response.json().catch(() => ({}))
    throw new Error(problem.detail || `Request failed (${response.status})`)
  }
  return response.json()
}

export function useResource<T>(
  path: string,
  refresh = 0,
): { data?: T; error?: string } {
  const [result, setResult] = useState<{
    path: string
    refresh: number
    data?: T
    error?: string
  }>()
  useEffect(() => {
    if (!path) return
    let active = true
    api<T>(path)
      .then((data) => active && setResult({ path, refresh, data }))
      .catch(
        (error) => active && setResult({ path, refresh, error: error.message }),
      )
    return () => {
      active = false
    }
  }, [path, refresh])
  return result?.path === path && result.refresh === refresh ? result : {}
}

export function useAction() {
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function run(action: () => Promise<void>) {
    setError('')
    setBusy(true)
    try {
      await action()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed')
    } finally {
      setBusy(false)
    }
  }
  return { run, busy, error }
}
