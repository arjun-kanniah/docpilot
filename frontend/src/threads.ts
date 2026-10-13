import type { Turn } from './ChatTurn'

/** A saved conversation and the documents it searches (null: the whole library). */
export type Thread = {
  id: string
  title: string
  turns: Turn[]
  documentIds: string[] | null
  updatedAt: number
}

const KEY = 'docpilot.threads'
const MAX_THREADS = 30
const TITLE_CHARS = 60

function makeId(): string {
  // randomUUID needs a secure context (HTTPS or localhost); a LAN address over HTTP isn't one
  return typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`
}

export function newThread(documentIds: string[] | null = null): Thread {
  return { id: makeId(), title: '', turns: [], documentIds, updatedAt: Date.now() }
}

export function titleFor(question: string): string {
  const line = question.trim().replace(/\s+/g, ' ')
  return line.length > TITLE_CHARS ? `${line.slice(0, TITLE_CHARS - 1)}…` : line
}

/** Earlier turns to send with a follow-up: finished ones that produced an answer. */
export function historyFor(turns: Turn[]): { question: string; answer: string }[] {
  return turns
    .filter((t) => !t.pending && !t.error && t.answer)
    .map((t) => ({ question: t.question, answer: t.answer }))
}

/**
 * The documents a request should search: the thread's choice, minus any since deleted.
 * null means the whole library, including when nothing chosen still exists.
 */
export function scopeFor(thread: Thread, existing: string[]): string[] | null {
  if (thread.documentIds === null) return null
  const kept = thread.documentIds.filter((id) => existing.includes(id))
  return kept.length > 0 && kept.length < existing.length ? kept : null
}

/** Saved threads, most recent first. Storage can be missing or blocked: then there are none. */
export function loadThreads(): Thread[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(KEY) ?? '[]')
    if (!Array.isArray(parsed)) return []
    return (parsed as Thread[])
      .filter((t) => typeof t?.id === 'string' && Array.isArray(t.turns))
      .map((t) => ({ ...t, turns: t.turns.map((turn) => ({ ...turn, pending: false })) }))
  } catch {
    return []
  }
}

/** Keep the most recent threads that have turns; drop the oldest if storage is full. */
export function saveThreads(threads: Thread[]): void {
  let kept = threads
    .filter((t) => t.turns.length > 0)
    .sort((a, b) => b.updatedAt - a.updatedAt)
    .slice(0, MAX_THREADS)
  while (kept.length > 0) {
    try {
      localStorage.setItem(KEY, JSON.stringify(kept))
      return
    } catch {
      kept = kept.slice(0, -1) // quota exceeded, or storage blocked: try with fewer
    }
  }
}
