import { type DragEvent, useState } from 'react'
import type { DocumentInfo } from './api'

const ACCEPTED = '.pdf,.md,.markdown,.txt'

export type Notice = { kind: 'ok' | 'error'; text: string }

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

type Props = {
  documents: DocumentInfo[]
  /** Public demo: the library is fixed, so uploads and deletes are hidden. */
  readOnly: boolean
  uploading: boolean
  notice: Notice | null
  onUpload: (files: FileList) => void
  onDelete: (doc: DocumentInfo) => void
  /** Documents the current chat searches; null means all of them. */
  scope: string[] | null
  onScopeChange: (scope: string[] | null) => void
  scopeLocked: boolean
}

/** Upload (button or drag and drop) and the list of indexed documents. */
export function DocumentsPanel({
  documents,
  readOnly,
  uploading,
  notice,
  onUpload,
  onDelete,
  scope,
  onScopeChange,
  scopeLocked,
}: Props) {
  const allIds = documents.map((d) => d.id)
  const inScope = (id: string) => scope === null || scope.includes(id)
  const chosen = allIds.filter(inScope)

  function toggle(id: string) {
    const next = inScope(id) ? chosen.filter((x) => x !== id) : [...chosen, id]
    if (next.length === 0) return // a chat searches at least one document
    onScopeChange(next.length === allIds.length ? null : next)
  }

  const [dragging, setDragging] = useState(false)

  function handleDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    if (!readOnly && !uploading && event.dataTransfer.files.length) {
      onUpload(event.dataTransfer.files)
    }
  }

  return (
    <section
      className={`documents ${dragging ? 'dragging' : ''}`}
      aria-label="Documents"
      onDragOver={(e) => {
        e.preventDefault()
        if (!readOnly) setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      {readOnly ? (
        <p className="demo-note">
          <strong>Public demo.</strong> Ask about Aurora Instruments, a fictional company whose
          documents are loaded here; newer ones update some older figures. Uploads are off;{' '}
          <a href="https://github.com/arjun-kanniah/docpilot" target="_blank" rel="noreferrer">
            run DocPilot locally
          </a>{' '}
          to use your own files.
        </p>
      ) : (
        <>
          <label className={`button upload ${uploading ? 'disabled' : ''}`}>
            {uploading ? 'Indexing…' : '+ Upload files'}
            <input
              type="file"
              accept={ACCEPTED}
              multiple
              hidden
              disabled={uploading}
              onChange={(e) => {
                if (e.target.files?.length) onUpload(e.target.files)
                e.target.value = ''
              }}
            />
          </label>
          <p className="hint">PDF, Markdown or text, up to 20 MB. Or drop files here.</p>
        </>
      )}

      {notice && (
        <p className={`notice notice-${notice.kind}`} role="status">
          {notice.text}
        </p>
      )}

      <h2 className="section-label">
        Documents{' '}
        <span className="count">
          {chosen.length < documents.length
            ? `${chosen.length} of ${documents.length} in this chat`
            : documents.length}
        </span>
      </h2>
      {documents.length === 0 ? (
        <p className="hint">Nothing indexed yet.</p>
      ) : (
        <ul className="doc-list">
          {documents.map((doc) => (
            <li key={doc.id} title={doc.filename}>
              <input
                type="checkbox"
                className="scope-check"
                checked={inScope(doc.id)}
                disabled={scopeLocked || (inScope(doc.id) && chosen.length === 1)}
                onChange={() => toggle(doc.id)}
                aria-label={`Use ${doc.filename} in this chat`}
                title="Use in this chat"
              />
              <div>
                <span className="doc-name">{doc.filename}</span>
                <span className="doc-meta">
                  {formatSize(doc.size_bytes)}
                  {doc.page_count ? ` · ${doc.page_count} pp` : ''} · {doc.chunk_count} chunks
                </span>
              </div>
              {!readOnly && (
                <button
                  type="button"
                  className="icon-button"
                  onClick={() => onDelete(doc)}
                  aria-label={`Delete ${doc.filename}`}
                  title="Delete"
                >
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
