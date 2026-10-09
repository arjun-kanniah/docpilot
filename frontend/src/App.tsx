import { useEffect, useState } from 'react'

type Health = { status: string; version: string; env: string }

type ApiState =
  | { kind: 'loading' }
  | { kind: 'ok'; health: Health }
  | { kind: 'error'; message: string }

function App() {
  const [api, setApi] = useState<ApiState>({ kind: 'loading' })

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json() as Promise<Health>
      })
      .then((health) => setApi({ kind: 'ok', health }))
      .catch((err: unknown) =>
        setApi({ kind: 'error', message: err instanceof Error ? err.message : String(err) }),
      )
  }, [])

  return (
    <main>
      <h1>DocPilot</h1>
      <p className="tagline">Ask questions about your documents and get answers with citations.</p>
      <section className="card" aria-live="polite">
        {api.kind === 'loading' && <span>Connecting to the API…</span>}
        {api.kind === 'ok' && (
          <span className="status-ok">
            API online · v{api.health.version} · {api.health.env}
          </span>
        )}
        {api.kind === 'error' && (
          <span className="status-error">API unreachable ({api.message}). Is `just dev-api` running?</span>
        )}
      </section>
    </main>
  )
}

export default App
