import type { AgentUsage, AskUsage, SearchHit, TraceItem } from './api'
import { Answer } from './Answer'
import { Trace } from './Trace'

export type Mode = 'ask' | 'research'

export type Turn = {
  id: number
  mode: Mode
  question: string
  answer: string
  sources: SearchHit[] | null
  usage: AskUsage | AgentUsage | null
  trace: TraceItem[]
  /** A follow-up as the server rewrote it to stand alone, which is what was searched for. */
  rewrite: string | null
  error: string | null
  pending: boolean
}

/** One question (or research task) and its streamed answer, with the sources it cites. */
export function ChatTurn({ turn }: { turn: Turn }) {
  const prefix = `turn-${turn.id}-source-`
  const sources = turn.sources ?? []

  return (
    <article className="turn">
      <p className="question">
        {turn.mode === 'research' && <span className="mode-tag">Research</span>}
        {turn.question}
      </p>
      <div className="reply" aria-live={turn.pending ? 'polite' : 'off'}>
        {turn.rewrite && (
          <p className="rewrite muted" title="A follow-up, rewritten with what it refers to">
            {turn.mode === 'ask' ? 'Searched for' : 'Researched'}: {turn.rewrite}
          </p>
        )}
        {turn.mode === 'research' && (
          <Trace items={turn.trace} running={turn.pending && !turn.answer} />
        )}
        {turn.answer ? (
          <Answer text={turn.answer} sourceCount={sources.length} sourceIdPrefix={prefix} />
        ) : (
          turn.pending && (
            <p className="muted typing">{pendingLabel(turn)}</p>
          )
        )}
        {turn.error && <p className="notice notice-error">{turn.error}</p>}

        {sources.length > 0 && (
          <details className="sources">
            <summary>
              {sources.length} sources
              {turn.usage && ` · ${usageLabel(turn.usage)}`}
            </summary>
            <ol className="hits">
              {sources.map((hit, i) => (
                <li key={hit.chunk_id} id={`${prefix}${i + 1}`}>
                  <div className="hit-meta">
                    <span>
                      <span className="cite">{i + 1}</span> {hit.filename}
                      {hit.page ? `, page ${hit.page}` : ''}
                    </span>
                    <span className="score" title="Similarity to the question">
                      {hit.score.toFixed(2)}
                    </span>
                  </div>
                  <p>{hit.text}</p>
                </li>
              ))}
            </ol>
          </details>
        )}
      </div>
    </article>
  )
}

function pendingLabel(turn: Turn): string {
  if (turn.mode === 'ask') return turn.sources ? 'Thinking…' : 'Finding passages…'
  const last = turn.trace.findLast((item) => item.kind === 'step')
  return last?.kind === 'step' && last.step === 'writer' ? 'Writing…' : 'Researching…'
}

function usageLabel(usage: AskUsage | AgentUsage): string {
  const parts = [usage.model]
  if ('rounds' in usage && usage.rounds !== undefined) {
    parts.push(`${usage.rounds} round${usage.rounds === 1 ? '' : 's'}`)
  }
  if (usage.input_tokens !== undefined && usage.output_tokens !== undefined) {
    parts.push(
      `${usage.input_tokens.toLocaleString()} in / ${usage.output_tokens.toLocaleString()} out tokens`,
    )
  }
  return parts.join(' · ')
}
