import { useMemo } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { linkCitations, SOURCE_HREF } from './citations'

/** Open the collapsed source list a citation points into, before the browser scrolls to it. */
function revealSource(id: string) {
  document.getElementById(id)?.closest('details')?.setAttribute('open', '')
}

type Props = {
  text: string
  sourceCount: number
  /** Element id prefix for the sources (id = prefix + n), unique per answer. */
  sourceIdPrefix: string
}

/**
 * Render a model answer as Markdown (GitHub flavour, for tables). Answers are shaped by
 * uploaded documents, so raw HTML is dropped and images are not rendered: an image URL
 * could leak data to another site the moment it loads.
 */
export function Answer({ text, sourceCount, sourceIdPrefix }: Props) {
  const components = useMemo<Components>(
    () => ({
      a: ({ href = '', children }) => {
        const source = SOURCE_HREF.exec(href)?.[1]
        if (source) {
          const id = `${sourceIdPrefix}${source}`
          return (
            <a
              className="cite"
              href={`#${id}`}
              onClick={() => revealSource(id)}
              aria-label={`Source ${source}`}
            >
              {children}
            </a>
          )
        }
        return (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        )
      },
      // Wide tables scroll inside the answer instead of stretching the page on phones
      table: ({ children }) => (
        <div className="table-wrap">
          <table>{children}</table>
        </div>
      ),
    }),
    [sourceIdPrefix],
  )

  return (
    <div className="markdown">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={components}
        skipHtml
        disallowedElements={['img']}
      >
        {linkCitations(text, sourceCount)}
      </Markdown>
    </div>
  )
}
