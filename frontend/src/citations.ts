/**
 * Turn citation markers like [2], or lists like [1, 2] that some models write, into Markdown
 * links to the numbered sources, so the Markdown renderer can show them as chips. Markers
 * with a number outside 1..sourceCount, and real Markdown links such as [2](https://…), are
 * left alone.
 */
export function linkCitations(text: string, sourceCount: number): string {
  return text.replace(/\[(\d+(?:\s*,\s*\d+)*)\](?!\()/g, (marker, list: string) => {
    const numbers = list.split(',').map(Number)
    if (!numbers.every((n) => n >= 1 && n <= sourceCount)) return marker
    return numbers.map((n) => `[${n}](#source-${n})`).join('')
  })
}

export const SOURCE_HREF = /^#source-(\d+)$/
