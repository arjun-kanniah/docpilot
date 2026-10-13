import type { Thread } from './threads'

type Props = {
  threads: Thread[]
  activeId: string
  disabled: boolean
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

/** Saved chats, newest first. They live in this browser only. */
export function ChatList({ threads, activeId, disabled, onSelect, onDelete }: Props) {
  const saved = threads.filter((t) => t.turns.length > 0)
  if (saved.length === 0) return null
  return (
    <section className="chats" aria-label="Chats">
      <h2 className="section-label">Chats</h2>
      <ul className="chat-list">
        {saved.map((thread) => (
          <li key={thread.id} className={thread.id === activeId ? 'active' : ''}>
            <button
              type="button"
              className="chat-link"
              onClick={() => onSelect(thread.id)}
              disabled={disabled}
              aria-current={thread.id === activeId ? 'true' : undefined}
              title={thread.title}
            >
              {thread.title || 'Untitled chat'}
            </button>
            <button
              type="button"
              className="icon-button"
              onClick={() => onDelete(thread.id)}
              disabled={disabled}
              aria-label={`Delete chat: ${thread.title}`}
              title="Delete chat"
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
