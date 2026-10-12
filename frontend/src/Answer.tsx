import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { linkCitations, SOURCE_HREF } from './citations'

const components: Components = {
  a: ({ href = '', children }) => {
    const source = SOURCE_HREF.exec(href)?.[1]
    if (source) {
      return (
        <a className="cite" href={href} aria-label={`Source ${source}`}>
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
}

/**
 * Render a model answer as Markdown (GitHub flavour, for tables). Answers are shaped by
 * uploaded documents, so raw HTML is dropped and images are not rendered: an image URL
 * could leak data to another site the moment it loads.
 */
export function Answer({ text, sourceCount }: { text: string; sourceCount: number }) {
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
