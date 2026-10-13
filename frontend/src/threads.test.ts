import { beforeEach, describe, expect, it } from 'vitest'
import type { Turn } from './ChatTurn'
import { historyFor, loadThreads, newThread, saveThreads, scopeFor, titleFor } from './threads'

function turn(id: number, patch: Partial<Turn> = {}): Turn {
  return {
    id,
    mode: 'ask',
    question: `q${id}`,
    answer: `a${id}`,
    sources: [],
    usage: null,
    trace: [],
    rewrite: null,
    error: null,
    pending: false,
    ...patch,
  }
}

const store = new Map<string, string>()
beforeEach(() => {
  store.clear()
  globalThis.localStorage = {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => void store.set(k, v),
  } as Storage
})

describe('threads', () => {
  it('sends only finished, answered turns as history', () => {
    const turns = [
      turn(1),
      turn(2, { error: 'Stopped.' }),
      turn(3, { pending: true }),
      turn(4, { answer: '' }),
    ]
    expect(historyFor(turns)).toEqual([{ question: 'q1', answer: 'a1' }])
  })

  it('scopes to the chosen documents that still exist', () => {
    const thread = { ...newThread(), documentIds: ['a', 'gone'] }
    expect(scopeFor(thread, ['a', 'b'])).toEqual(['a'])
    expect(scopeFor({ ...thread, documentIds: ['gone'] }, ['a', 'b'])).toBeNull()
    expect(scopeFor({ ...thread, documentIds: ['a', 'b'] }, ['a', 'b'])).toBeNull()
    expect(scopeFor(newThread(), ['a'])).toBeNull()
  })

  it('titles a thread from its first question', () => {
    expect(titleFor('  How long\nis the warranty?  ')).toBe('How long is the warranty?')
    expect(titleFor('x'.repeat(80))).toHaveLength(60)
  })

  it('saves threads with turns, newest first, and loads them as not pending', () => {
    const old = { ...newThread(), updatedAt: 1, turns: [turn(1)] }
    const recent = { ...newThread(), updatedAt: 2, turns: [turn(2, { pending: true })] }
    saveThreads([old, newThread(), recent])

    const loaded = loadThreads()
    expect(loaded.map((t) => t.id)).toEqual([recent.id, old.id])
    expect(loaded[0].turns[0].pending).toBe(false)
  })

  it('drops the oldest threads when storage is full', () => {
    const threads = [1, 2, 3].map((n) => ({ ...newThread(), updatedAt: n, turns: [turn(n)] }))
    globalThis.localStorage.setItem = (k: string, v: string) => {
      if (JSON.parse(v).length > 2) throw new Error('QuotaExceededError')
      store.set(k, v)
    }
    saveThreads(threads)
    expect(loadThreads().map((t) => t.updatedAt)).toEqual([3, 2])
  })

  it('treats unreadable storage as empty', () => {
    store.set('docpilot.threads', '{not json')
    expect(loadThreads()).toEqual([])
  })
})
