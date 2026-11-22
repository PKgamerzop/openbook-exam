import { useEffect, useState } from 'react'
import { Portal } from './Portal'
import { checkBackend, type ConnectionStatus } from './health'

const statusText: Record<ConnectionStatus, string> = {
  checking: 'Checking backend connection…',
  connected: 'API and database connected',
  degraded: 'API connected. Database unavailable.',
  unreachable: 'API health check unavailable',
}

export function App() {
  return <main className="app-shell"><Portal /></main>
}

export function Diagnostics() {
  const [status, setStatus] = useState<ConnectionStatus>('checking')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    void checkBackend(AbortSignal.any([controller.signal, AbortSignal.timeout(5000)]))
      .then((result) => {
        if (!controller.signal.aborted) setStatus(result)
      })
    return () => controller.abort()
  }, [attempt])

  return (
    <details className="diagnostics">
      <summary>Connection diagnostics</summary>
      <section aria-labelledby="connection">
        <h2 id="connection">Backend connection</h2>
        <p role="status" data-state={status}>{statusText[status]}</p>
        <button
          disabled={status === 'checking'}
          onClick={() => {
            setStatus('checking')
            setAttempt((previous) => previous + 1)
          }}
        >
          Check again
        </button>
      </section>
    </details>
  )
}
