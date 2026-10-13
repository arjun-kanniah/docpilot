import type { TraceItem } from './api'

const STEP_LABELS = {
  researcher: 'Researcher',
  analyst: 'Analyst',
  writer: 'Writer',
} as const

const STEP_ROLES = {
  researcher: 'searches the library and takes notes',
  analyst: 'checks the notes against the task',
  writer: 'writes the answer from the notes',
} as const

const STOP_REASONS = {
  round_limit: 'Stopping at the research round limit; the writer will say what is missing.',
  no_new_passages:
    'Stopping: the last round found no new passages, so the writer will say what is missing.',
} as const

function toolLabel(item: Extract<TraceItem, { kind: 'tool' }>): string {
  const query = typeof item.args.query === 'string' ? `“${item.args.query}”` : ''
  return item.name === 'search_library' ? `Searched ${query}` : 'Listed the documents'
}

/** What an agent run did, step by step: open while it runs, folded away once answered. */
export function Trace({ items, running }: { items: TraceItem[]; running: boolean }) {
  if (items.length === 0) return null
  const searches = items.filter((i) => i.kind === 'tool').length
  const rounds = items.filter((i) => i.kind === 'step' && i.step === 'researcher').length

  return (
    <details className="trace" open={running || undefined}>
      <summary>
        {running ? 'Working…' : 'How this answer was researched'} · {rounds} research round
        {rounds === 1 ? '' : 's'}, {searches} tool call{searches === 1 ? '' : 's'}
      </summary>
      <ol className="trace-list">
        {items.map((item, i) => {
          switch (item.kind) {
            case 'step':
              return (
                <li key={i} className="trace-step">
                  <strong>{STEP_LABELS[item.step]}</strong>
                  {item.round && item.step !== 'writer' ? ` · round ${item.round}` : ''}
                  <span className="muted"> · {STEP_ROLES[item.step]}</span>
                </li>
              )
            case 'tool':
              return (
                <li key={i} className="trace-tool">
                  {toolLabel(item)} <span className="muted">→ {item.summary}</span>
                </li>
              )
            case 'notes':
              return (
                <li key={i}>
                  <details className="trace-notes trace-detail">
                    <summary>Research notes</summary>
                    <p>{item.text}</p>
                  </details>
                </li>
              )
            case 'review':
              return (
                <li key={i} className="trace-review">
                  <span>
                    {item.gaps.length === 0
                      ? 'Enough to write.'
                      : item.next === 'researcher'
                        ? 'Needs more research:'
                        : `${STOP_REASONS[item.stop_reason ?? 'round_limit']} Still missing:`}
                  </span>
                  {item.gaps.length > 0 && (
                    <ul>
                      {item.gaps.map((gap) => (
                        <li key={gap}>{gap}</li>
                      ))}
                    </ul>
                  )}
                  {item.corrections.length > 0 && (
                    <details className="trace-detail">
                      <summary>
                        {item.corrections.length} correction
                        {item.corrections.length === 1 ? '' : 's'} for the writer
                      </summary>
                      <ul>
                        {item.corrections.map((fix) => (
                          <li key={fix}>{fix}</li>
                        ))}
                      </ul>
                    </details>
                  )}
                  {item.summary && (
                    <details className="trace-detail">
                      <summary>Analyst&apos;s notes</summary>
                      <p>{item.summary}</p>
                    </details>
                  )}
                </li>
              )
          }
        })}
      </ol>
    </details>
  )
}
