import { type FormEvent, useCallback, useEffect, useRef, useState } from 'react'
import {
  api,
  type AskUsage,
  type DocumentInfo,
  type Health,
  type ModelsInfo,
  type SearchHit,
} from './api'
import { Answer } from './Answer'

const ACCEPTED = '.pdf,.md,.markdown,.txt'
const MODEL_KEY = 'docpilot.model'

function loadModelChoice(): string | null {
  try {
    return localStorage.getItem(MODEL_KEY)
  } catch {
    return null
  }
}

function saveModelChoice(value: string) {
  try {
    localStorage.setItem(MODEL_KEY, value)
  } catch {
    // storage unavailable (private mode): the choice just isn't remembered
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [uploading, setUploading] = useState(false)
  const [notice, setNotice] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)
  const [models, setModels] = useState<ModelsInfo | null>(null)
  const [modelChoice, setModelChoice] = useState('')
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)
  const [answer, setAnswer] = useState('')
  const [sources, setSources] = useState<SearchHit[] | null>(null)
  const [usage, setUsage] = useState<AskUsage | null>(null)
  const [askError, setAskError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const refreshDocuments = useCallback(() => {
    api
      .listDocuments()
      .then(setDocuments)
      .catch((err: unknown) => setNotice({ kind: 'error', text: errorMessage(err) }))
  }, [])

  useEffect(() => {
    api
      .health()
      .then(setHealth)
      .catch((err: unknown) => setHealthError(errorMessage(err)))
    api
      .models()
      .then((info) => {
        setModels(info)
        const options = info.providers.flatMap((p) => p.models.map((m) => `${p.id}:${m}`))
        const saved = loadModelChoice()
        const fallback = info.default ? `${info.default.provider}:${info.default.model}` : ''
        setModelChoice(saved && options.includes(saved) ? saved : fallback)
      })
      .catch(() => setModels({ providers: [], default: null }))
    refreshDocuments()
  }, [refreshDocuments])

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return
    setUploading(true)
    setNotice(null)
    const messages: string[] = []
    for (const file of Array.from(files)) {
      try {
        const result = await api.uploadDocument(file)
        messages.push(
          result.duplicate
            ? `${file.name}: already uploaded`
            : `${file.name}: ${result.document.chunk_count} chunks indexed`,
        )
      } catch (err) {
        setNotice({ kind: 'error', text: `${file.name}: ${errorMessage(err)}` })
      }
    }
    if (messages.length) setNotice({ kind: 'ok', text: messages.join(' · ') })
    setUploading(false)
    refreshDocuments()
  }

  async function handleDelete(doc: DocumentInfo) {
    try {
      await api.deleteDocument(doc.id)
      refreshDocuments()
    } catch (err) {
      setNotice({ kind: 'error', text: errorMessage(err) })
    }
  }

  async function handleAsk(event: FormEvent) {
    event.preventDefault()
    if (!question.trim() || asking) return
    const [provider, model] = modelChoice.split(':')
    const controller = new AbortController()
    abortRef.current = controller
    setAsking(true)
    setAnswer('')
    setSources(null)
    setUsage(null)
    setAskError(null)
    try {
      await api.ask(
        { question: question.trim(), provider: provider || undefined, model: model || undefined },
        {
          onSources: setSources,
          onDelta: (text) => setAnswer((current) => current + text),
          onDone: setUsage,
          onError: setAskError,
        },
        controller.signal,
      )
    } catch (err) {
      if (!controller.signal.aborted) setAskError(errorMessage(err))
    } finally {
      abortRef.current = null
      setAsking(false)
    }
  }

  return (
    <main>
      <header className="header">
        <div>
          <h1>DocPilot</h1>
          <p className="tagline">Ask questions about your documents and get answers with citations.</p>
        </div>
        <span
          className={`status ${health ? 'status-ok' : healthError ? 'status-error' : ''}`}
          title={healthError ?? undefined}
        >
          {health ? `API v${health.version}` : healthError ? 'API offline' : 'Connecting…'}
        </span>
      </header>

      {notice && (
        <p className={`notice notice-${notice.kind}`} role="status">
          {notice.text}
        </p>
      )}

      <section className="card">
        <div className="card-head">
          <h2>Documents</h2>
          <label className={`button ${uploading ? 'disabled' : ''}`}>
            {uploading ? 'Indexing…' : 'Upload files'}
            <input
              type="file"
              accept={ACCEPTED}
              multiple
              hidden
              disabled={uploading}
              onChange={(e) => {
                void handleUpload(e.target.files)
                e.target.value = ''
              }}
            />
          </label>
        </div>
        {documents.length === 0 ? (
          <p className="muted">No documents yet. Upload a PDF, Markdown or text file to start.</p>
        ) : (
          <ul className="doc-list">
            {documents.map((doc) => (
              <li key={doc.id}>
                <div>
                  <strong>{doc.filename}</strong>
                  <span className="muted">
                    {formatSize(doc.size_bytes)}
                    {doc.page_count ? ` · ${doc.page_count} pages` : ''} · {doc.chunk_count} chunks
                  </span>
                </div>
                <button
                  type="button"
                  className="link-button"
                  onClick={() => void handleDelete(doc)}
                  aria-label={`Delete ${doc.filename}`}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <div className="card-head">
          <h2>Ask</h2>
          {models && models.providers.length > 0 && (
            <select
              className="model-select"
              value={modelChoice}
              onChange={(e) => {
                setModelChoice(e.target.value)
                saveModelChoice(e.target.value)
              }}
              aria-label="Model"
              disabled={asking}
            >
              {models.providers.map((p) => (
                <optgroup key={p.id} label={p.label}>
                  {p.models.map((m) => (
                    <option key={m} value={`${p.id}:${m}`}>
                      {m}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          )}
        </div>
        {models && models.providers.length === 0 && (
          <p className="muted">
            No LLM provider is configured. Add ANTHROPIC_API_KEY or GEMINI_API_KEY to .env and
            restart the API.
          </p>
        )}
        <form className="search" onSubmit={(e) => void handleAsk(e)}>
          <input
            type="search"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. Is water damage covered?"
            aria-label="Question"
          />
          {asking ? (
            <button type="button" className="button" onClick={() => abortRef.current?.abort()}>
              Stop
            </button>
          ) : (
            <button type="submit" className="button" disabled={!question.trim() || !modelChoice}>
              Ask
            </button>
          )}
        </form>

        {(answer || asking || askError) && (
          <div className="answer" aria-live="polite">
            {answer ? (
              <Answer text={answer} sourceCount={sources?.length ?? 0} />
            ) : (
              asking && <p className="muted">{sources ? 'Thinking…' : 'Finding passages…'}</p>
            )}
            {askError && <p className="notice-error">{askError}</p>}
            {usage && (
              <p className="muted usage">
                {usage.model} · {usage.input_tokens.toLocaleString()} in /{' '}
                {usage.output_tokens.toLocaleString()} out tokens
              </p>
            )}
          </div>
        )}

        {sources && sources.length > 0 && (
          <div>
            <h3>Sources</h3>
            <ol className="hits">
              {sources.map((hit, i) => (
                <li key={hit.chunk_id} id={`source-${i + 1}`}>
                  <div className="hit-meta">
                    <span>
                      <span className="cite">{i + 1}</span> {hit.filename}
                      {hit.page ? `, page ${hit.page}` : ''}
                    </span>
                    <span className="score" title="Similarity to the question">
                      {hit.score.toFixed(2)}
                    </span>
                  </div>
                  <details>
                    <summary>Passage</summary>
                    <p>{hit.text}</p>
                  </details>
                </li>
              ))}
            </ol>
          </div>
        )}
      </section>
    </main>
  )
}

export default App
