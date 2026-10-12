import type { AskUsage, SearchHit } from './api'
import { Answer } from './Answer'

export type Turn = {
  id: number
  question: string
  answer: string
  sources: SearchHit[] | null
  usage: AskUsage | null
  error: string | null
  pending: boolean
}

/** One question and its streamed answer, with the sources its citations point to. */
export function ChatTurn({ turn }: { turn: Turn }) {
  const prefix = `turn-${turn.id}-source-`
  const sources = turn.sources ?? []

  return (
    <article className="turn">
      <p className="question">{turn.question}</p>
      <div className="reply" aria-live={turn.pending ? 'polite' : 'off'}>
        {turn.answer ? (
          <Answer text={turn.answer} sourceCount={sources.length} sourceIdPrefix={prefix} />
        ) : (
          turn.pending && (
            <p className="muted typing">{turn.sources ? 'Thinking…' : 'Finding passages…'}</p>
          )
        )}
        {turn.error && <p className="notice notice-error">{turn.error}</p>}

        {sources.length > 0 && (
          <details className="sources">
            <summary>
              {sources.length} sources
              {turn.usage &&
                ` · ${turn.usage.model} · ${turn.usage.input_tokens.toLocaleString()} in / ` +
                  `${turn.usage.output_tokens.toLocaleString()} out tokens`}
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
