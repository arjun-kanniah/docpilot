/**
 * Turn citation markers like [2] into Markdown links to the numbered sources, so the
 * Markdown renderer can show them as chips. Markers outside 1..sourceCount, and real
 * Markdown links such as [2](https://…), are left alone.
 */
export function linkCitations(text: string, sourceCount: number): string {
  return text.replace(/\[(\d+)\](?!\()/g, (marker, digits: string) => {
    const n = Number(digits)
    return n >= 1 && n <= sourceCount ? `[${n}](#source-${n})` : marker
  })
}

export const SOURCE_HREF = /^#source-(\d+)$/
