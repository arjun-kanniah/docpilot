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
  uploading: boolean
  notice: Notice | null
  onUpload: (files: FileList) => void
  onDelete: (doc: DocumentInfo) => void
}

/** Upload (button or drag and drop) and the list of indexed documents. */
export function DocumentsPanel({ documents, uploading, notice, onUpload, onDelete }: Props) {
  const [dragging, setDragging] = useState(false)

  function handleDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    if (!uploading && event.dataTransfer.files.length) onUpload(event.dataTransfer.files)
  }

  return (
    <section
      className={`documents ${dragging ? 'dragging' : ''}`}
      aria-label="Documents"
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
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

      {notice && (
        <p className={`notice notice-${notice.kind}`} role="status">
          {notice.text}
        </p>
      )}

      <h2 className="section-label">
        Documents <span className="count">{documents.length}</span>
      </h2>
      {documents.length === 0 ? (
        <p className="hint">Nothing indexed yet.</p>
      ) : (
        <ul className="doc-list">
          {documents.map((doc) => (
            <li key={doc.id} title={doc.filename}>
              <div>
                <span className="doc-name">{doc.filename}</span>
                <span className="doc-meta">
                  {formatSize(doc.size_bytes)}
                  {doc.page_count ? ` · ${doc.page_count} pp` : ''} · {doc.chunk_count} chunks
                </span>
              </div>
              <button
                type="button"
                className="icon-button"
                onClick={() => onDelete(doc)}
                aria-label={`Delete ${doc.filename}`}
                title="Delete"
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
