export type Health = { status: string; version: string; env: string; demo: boolean }

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

export type ProviderInfo = { id: string; label: string; models: string[] }

export type ModelChoice = { provider: string; model: string }

export type ModelsInfo = { providers: ProviderInfo[]; default: ModelChoice | null }

export type AskUsage = ModelChoice & { input_tokens: number; output_tokens: number }

export type AskHandlers = {
  onSources: (sources: SearchHit[]) => void
  onDelta: (text: string) => void
  onDone: (usage: AskUsage) => void
  onError: (message: string) => void
}

async function errorDetail(res: Response): Promise<string> {
  const body = (await res.json().catch(() => null)) as { detail?: unknown } | null
  return typeof body?.detail === 'string' ? body.detail : `HTTP ${res.status}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init)
  if (!res.ok) throw new Error(await errorDetail(res))
  return (res.status === 204 ? undefined : await res.json()) as T
}

/** POST /api/ask and dispatch its Server-Sent Events. (EventSource only supports GET.) */
async function ask(
  body: { question: string } & Partial<ModelChoice>,
  handlers: AskHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) throw new Error(await errorDetail(res))

  const dispatch = (block: string) => {
    let event = 'message'
    let data = ''
    for (const line of block.split('\n')) {
      if (line.startsWith('event: ')) event = line.slice(7)
      else if (line.startsWith('data: ')) data += line.slice(6)
    }
    if (!data) return // keep-alive comment
    const payload: unknown = JSON.parse(data)
    if (event === 'sources') handlers.onSources(payload as SearchHit[])
    else if (event === 'delta') handlers.onDelta((payload as { text: string }).text)
    else if (event === 'done') handlers.onDone(payload as AskUsage)
    else if (event === 'error') handlers.onError((payload as { message: string }).message)
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    let end
    while ((end = buffer.indexOf('\n\n')) >= 0) {
      dispatch(buffer.slice(0, end))
      buffer = buffer.slice(end + 2)
    }
  }
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
  models: () => request<ModelsInfo>('/api/models'),
  ask,
}
