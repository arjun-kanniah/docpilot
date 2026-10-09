export type Health = { status: string; version: string; env: string }

export type DocumentInfo = {
  id: string
  filename: string
  content_type: string
  size_bytes: number
  page_count: number | null
  chunk_count: number
  created_at: string
}

export type IngestResult = { document: DocumentInfo; duplicate: boolean }

export type SearchHit = {
  chunk_id: string
  document_id: string
  filename: string
  page: number | null
  text: string
  score: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null
    const detail = typeof body?.detail === 'string' ? body.detail : `HTTP ${res.status}`
    throw new Error(detail)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export const api = {
  health: () => request<Health>('/api/health'),
  listDocuments: () => request<DocumentInfo[]>('/api/documents'),
  uploadDocument: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<IngestResult>('/api/documents', { method: 'POST', body: form })
  },
  deleteDocument: (id: string) => request<void>(`/api/documents/${id}`, { method: 'DELETE' }),
  search: (query: string, k = 5) =>
    request<SearchHit[]>('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, k }),
    }),
}
