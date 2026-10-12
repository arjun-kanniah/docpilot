import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'
import { api, type DocumentInfo, type Health, type ModelsInfo } from './api'
import { ChatTurn, type Turn } from './ChatTurn'
import { DocumentsPanel, type Notice } from './DocumentsPanel'

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

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [uploading, setUploading] = useState(false)
  const [notice, setNotice] = useState<Notice | null>(null)
  const [docsOpen, setDocsOpen] = useState(false) // drawer on narrow screens
  const [models, setModels] = useState<ModelsInfo | null>(null)
  const [modelChoice, setModelChoice] = useState('')
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const [asking, setAsking] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const threadRef = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const nextTurnId = useRef(1)

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

  // Follow the streaming answer, unless the reader has scrolled up to read something
  useEffect(() => {
    const thread = threadRef.current
    if (thread && stickToBottom.current) thread.scrollTop = thread.scrollHeight
  }, [turns])

  async function handleUpload(files: FileList) {
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
    if (!window.confirm(`Delete ${doc.filename}? Its passages are removed from search.`)) return
    try {
      await api.deleteDocument(doc.id)
      refreshDocuments()
    } catch (err) {
      setNotice({ kind: 'error', text: errorMessage(err) })
    }
  }

  async function handleAsk(event?: FormEvent) {
    event?.preventDefault()
    const text = question.trim()
    if (!text || asking || !modelChoice) return
    const [provider, model] = modelChoice.split(':')
    const id = nextTurnId.current++
    const update = (patch: Partial<Turn> | ((turn: Turn) => Partial<Turn>)) =>
      setTurns((all) =>
        all.map((t) => {
          if (t.id !== id) return t
          return { ...t, ...(typeof patch === 'function' ? patch(t) : patch) }
        }),
      )

    const controller = new AbortController()
    abortRef.current = controller
    stickToBottom.current = true
    setQuestion('')
    setAsking(true)
    setTurns((all) => [
      ...all,
      { id, question: text, answer: '', sources: null, usage: null, error: null, pending: true },
    ])
    try {
      await api.ask(
        { question: text, provider, model },
        {
          onSources: (sources) => update({ sources }),
          onDelta: (delta) => update((t) => ({ answer: t.answer + delta })),
          onDone: (usage) => update({ usage }),
          onError: (error) => update({ error }),
        },
        controller.signal,
      )
    } catch (err) {
      update({ error: controller.signal.aborted ? 'Stopped.' : errorMessage(err) })
    } finally {
      update({ pending: false })
      abortRef.current = null
      setAsking(false)
    }
  }

  function handleComposerKey(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      void handleAsk()
    }
  }

  const docCount = `${documents.length} indexed document${documents.length === 1 ? '' : 's'}`
  const emptyMessage =
    models !== null && models.providers.length === 0
      ? 'No LLM provider is configured. Add ANTHROPIC_API_KEY, GEMINI_API_KEY or ' +
        'OPENAI_API_KEY to .env and restart the API.'
      : documents.length === 0
        ? 'Upload a PDF, Markdown or text file, then ask a question about it.'
        : `Answers come from your ${docCount}, with citations you can check.`

  return (
    <div className="app">
      <aside className={`sidebar ${docsOpen ? 'open' : ''}`}>
        <div className="brand">
          <h1>DocPilot</h1>
          <span
            className={`status-dot ${health ? 'status-ok' : healthError ? 'status-error' : ''}`}
            title={health ? `API v${health.version}` : (healthError ?? 'Connecting…')}
            aria-label={health ? 'API online' : healthError ? 'API offline' : 'Connecting'}
          />
          <button
            type="button"
            className="icon-button drawer-close"
            onClick={() => setDocsOpen(false)}
            aria-label="Close documents"
          >
            ×
          </button>
        </div>
        <DocumentsPanel
          documents={documents}
          readOnly={health?.demo ?? false}
          uploading={uploading}
          notice={notice}
          onUpload={(files) => void handleUpload(files)}
          onDelete={(doc) => void handleDelete(doc)}
        />
      </aside>
      {docsOpen && <div className="scrim" onClick={() => setDocsOpen(false)} aria-hidden />}

      <main className="chat">
        <header className="chat-head">
          <button
            type="button"
            className="ghost-button drawer-open"
            onClick={() => setDocsOpen(true)}
          >
            Documents ({documents.length})
          </button>
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
          {turns.length > 0 && (
            <button
              type="button"
              className="ghost-button new-chat"
              onClick={() => setTurns([])}
              disabled={asking}
            >
              New chat
            </button>
          )}
        </header>

        <div
          className="thread"
          ref={threadRef}
          onScroll={(e) => {
            const el = e.currentTarget
            stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80
          }}
        >
          {turns.length === 0 ? (
            <div className="empty">
              <h2>Ask your documents</h2>
              <p className="muted">{emptyMessage}</p>
            </div>
          ) : (
            <div className="turns">
              {turns.map((turn) => (
                <ChatTurn key={turn.id} turn={turn} />
              ))}
            </div>
          )}
        </div>

        <form className="composer" onSubmit={(e) => void handleAsk(e)}>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleComposerKey}
            placeholder="Ask a question about your documents…"
            aria-label="Question"
            rows={1}
            maxLength={2000}
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
        <p className="composer-hint">
          Each question is answered on its own from your documents. Enter to send, Shift+Enter
          for a new line.
        </p>
      </main>
    </div>
  )
}

export default App
