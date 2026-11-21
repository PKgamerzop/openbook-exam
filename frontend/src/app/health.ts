export type ConnectionStatus = 'checking' | 'connected' | 'degraded' | 'unreachable'

export async function checkBackend(signal: AbortSignal): Promise<ConnectionStatus> {
  try {
    const response = await fetch('/api/health', { signal, cache: 'no-store' })
    const health = await response.json()
    if (response.ok && health?.status === 'ok' && health.database === 'available') {
      return 'connected'
    }
    if (response.status === 503 && health?.status === 'degraded' &&
        health.database === 'unavailable') {
      return 'degraded'
    }
  } catch {
    return 'unreachable'
  }
  return 'unreachable'
}
