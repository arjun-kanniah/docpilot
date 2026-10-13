import { type FormEvent, type KeyboardEvent, useCallback, useEffect, useRef, useState } from 'react'
import { api, type DocumentInfo, type Health, type ModelsInfo, type SearchHit } from './api'
import { ChatList } from './ChatList'
import { ChatTurn, type Mode, type Turn } from './ChatTurn'
import { DocumentsPanel, type Notice } from './DocumentsPanel'
import {
  historyFor,
  loadThreads,
  newThread,
  saveThreads,
  scopeFor,
  type Thread,
  titleFor,
} from './threads'

const MODEL_KEY = 'docpilot.model'

const PLACEHOLDERS: Record<Mode, string> = {
  ask: 'Ask a question about your documents…',
  research: 'Give a research task, e.g. compare options and recommend one…',
}

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

/** Saved chats, plus a fresh one to start in. */
function startState() {
  const fresh = newThread()
  const saved = loadThreads()
  const lastTurnId = Math.max(0, ...saved.flatMap((t) => t.turns.map((turn) => turn.id)))
  return { threads: [fresh, ...saved], activeId: fresh.id, nextTurnId: lastTurnId + 1 }
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
  const [mode, setMode] = useState<Mode>('ask')
  const [start] = useState(startState)
  const [threads, setThreads] = useState<Thread[]>(start.threads)
  const [activeId, setActiveId] = useState(start.activeId)
  const [asking, setAsking] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const threadRef = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)
  const nextTurnId = useRef(start.nextTurnId)
  const active = threads.find((t) => t.id === activeId) ?? threads[0]
  const turns = active.turns

  const updateThread = (id: string, change: (thread: Thread) => Partial<Thread>) =>
    setThreads((all) => all.map((t) => (t.id === id ? { ...t, ...change(t) } : t)))

  // Save chats between answers, not on every streamed word
  useEffect(() => {
    if (!asking) saveThreads(threads)
  }, [threads, asking])

  function startNewChat() {
    if (active.turns.length === 0) return
    const fresh = newThread()
    setThreads((all) => [fresh, ...all.filter((t) => t.turns.length > 0)])
    setActiveId(fresh.id)
    stickToBottom.current = true
  }

  function selectChat(id: string) {
    setThreads((all) => all.filter((t) => t.turns.length > 0 || t.id === id))
    setActiveId(id)
    setDocsOpen(false)
    stickToBottom.current = true
  }

  function deleteChat(id: string) {
    if (id !== activeId) {
      setThreads((all) => all.filter((t) => t.id !== id))
      return
    }
    const fresh = newThread()
    setThreads((all) => [fresh, ...all.filter((t) => t.id !== id && t.turns.length > 0)])
    setActiveId(fresh.id)
  }

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
        // In a chat limited to some documents, a new upload joins them
        if (active.documentIds !== null && !active.documentIds.includes(result.document.id)) {
          const id = result.document.id
          updateThread(active.id, (t) => ({ documentIds: [...(t.documentIds ?? []), id] }))
        }
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
    const threadId = active.id
    const context = {
      history: historyFor(active.turns),
      document_ids: scopeFor(
        active,
        documents.map((d) => d.id),
      ),
    }
    const update = (patch: Partial<Turn> | ((turn: Turn) => Partial<Turn>)) =>
      updateThread(threadId, (thread) => ({
        turns: thread.turns.map((t) =>
          t.id === id ? { ...t, ...(typeof patch === 'function' ? patch(t) : patch) } : t,
        ),
      }))

    const controller = new AbortController()
    abortRef.current = controller
    stickToBottom.current = true
    setQuestion('')
    setAsking(true)
    updateThread(threadId, (thread) => ({
      title: thread.title || titleFor(text),
      updatedAt: Date.now(),
      turns: [
        ...thread.turns,
        {
          id,
          mode,
          question: text,
          answer: '',
          sources: null,
          usage: null,
          trace: [],
          rewrite: null,
          error: null,
          pending: true,
        },
      ],
    }))
    const handlers = {
      onRewrite: (rewrite: string) => update({ rewrite }),
      onSources: (sources: SearchHit[]) => update({ sources }),
      onDelta: (delta: string) => update((t) => ({ answer: t.answer + delta })),
      onDone: (usage: Turn['usage']) => update({ usage }),
      onError: (error: string) => update({ error }),
    }
    try {
      if (mode === 'research') {
        await api.agent(
          { task: text, provider, model, ...context },
          { ...handlers, onTrace: (item) => update((t) => ({ trace: [...t.trace, item] })) },
          controller.signal,
        )
      } else {
        await api.ask({ question: text, provider, model, ...context }, handlers, controller.signal)
      }
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
  const scoped = scopeFor(
    active,
    documents.map((d) => d.id),
  )
  const scopeNote = scoped
    ? `This chat searches ${scoped.length} of ${documents.length} documents.`
    : ''
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
        <button
          type="button"
          className="ghost-button sidebar-new-chat"
          onClick={() => {
            startNewChat()
            setDocsOpen(false)
          }}
          disabled={asking || turns.length === 0}
        >
          + New chat
        </button>
        <ChatList
          threads={threads}
          activeId={active.id}
          disabled={asking}
          onSelect={selectChat}
          onDelete={deleteChat}
        />
        <DocumentsPanel
          documents={documents}
          readOnly={health?.demo ?? false}
          uploading={uploading}
          notice={notice}
          onUpload={(files) => void handleUpload(files)}
          onDelete={(doc) => void handleDelete(doc)}
          scope={scopeFor(
            active,
            documents.map((d) => d.id),
          )}
          onScopeChange={(scope) => updateThread(active.id, () => ({ documentIds: scope }))}
          scopeLocked={asking}
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
            Chats & documents
          </button>
          <div className="mode-switch" role="group" aria-label="Mode">
            {(['ask', 'research'] as const).map((m) => (
              <button
                key={m}
                type="button"
                className={mode === m ? 'active' : ''}
                aria-pressed={mode === m}
                onClick={() => setMode(m)}
                disabled={asking}
              >
                {m === 'ask' ? 'Ask' : 'Research'}
              </button>
            ))}
          </div>
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
              onClick={startNewChat}
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
              <h2>{mode === 'ask' ? 'Ask your documents' : 'Research your documents'}</h2>
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
            placeholder={PLACEHOLDERS[mode]}
            aria-label={mode === 'ask' ? 'Question' : 'Research task'}
            rows={1}
            maxLength={2000}
          />
          {asking ? (
            <button type="button" className="button" onClick={() => abortRef.current?.abort()}>
              Stop
            </button>
          ) : (
            <button type="submit" className="button" disabled={!question.trim() || !modelChoice}>
              {mode === 'ask' ? 'Ask' : 'Research'}
            </button>
          )}
        </form>
        <p className="composer-hint">
          {mode === 'ask'
            ? 'Follow-up questions build on this chat.'
            : 'Research mode: a researcher searches, an analyst checks the notes, a writer ' +
              `answers. Slower${health?.demo ? ', and counts as 5 questions on the demo' : ''}.`}{' '}
          {scopeNote} Enter to send, Shift+Enter for a new line.
        </p>
      </main>
    </div>
  )
}

export default App
