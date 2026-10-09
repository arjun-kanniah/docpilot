import { type FormEvent, useCallback, useEffect, useState } from 'react'
import { api, type DocumentInfo, type Health, type SearchHit } from './api'

const ACCEPTED = '.pdf,.md,.markdown,.txt'

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
  const [query, setQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [hits, setHits] = useState<SearchHit[] | null>(null)

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
      setHits((current) => current?.filter((h) => h.document_id !== doc.id) ?? null)
      refreshDocuments()
    } catch (err) {
      setNotice({ kind: 'error', text: errorMessage(err) })
    }
  }

  async function handleSearch(event: FormEvent) {
    event.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    try {
      setHits(await api.search(query.trim()))
    } catch (err) {
      setNotice({ kind: 'error', text: errorMessage(err) })
    } finally {
      setSearching(false)
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
        <h2>Search</h2>
        <p className="muted">
          Finds the passages most similar in meaning to your question. Answers with citations come
          next.
        </p>
        <form className="search" onSubmit={(e) => void handleSearch(e)}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="e.g. Is water damage covered?"
            aria-label="Search query"
          />
          <button type="submit" className="button" disabled={searching || !query.trim()}>
            {searching ? 'Searching…' : 'Search'}
          </button>
        </form>
        {hits && hits.length === 0 && <p className="muted">No matches. Upload documents first.</p>}
        {hits && hits.length > 0 && (
          <ol className="hits">
            {hits.map((hit) => (
              <li key={hit.chunk_id}>
                <div className="hit-meta">
                  <span>
                    {hit.filename}
                    {hit.page ? `, page ${hit.page}` : ''}
                  </span>
                  <span className="score">{hit.score.toFixed(2)}</span>
                </div>
                <p>{hit.text}</p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </main>
  )
}

export default App
