import { describe, expect, it } from 'vitest'
import { linkCitations } from './citations'

describe('linkCitations', () => {
  it('links markers to their sources', () => {
    expect(linkCitations('Covered for a year [1][2].', 2)).toBe(
      'Covered for a year [1](#source-1)[2](#source-2).',
    )
  })

  it('leaves markers without a matching source alone', () => {
    expect(linkCitations('See [0] and [3].', 2)).toBe('See [0] and [3].')
  })

  it('leaves existing Markdown links alone', () => {
    expect(linkCitations('[1](https://example.com)', 1)).toBe('[1](https://example.com)')
  })

  it('works inside table cells', () => {
    expect(linkCitations('| Parts | 1 year [1] |', 1)).toBe('| Parts | 1 year [1](#source-1) |')
  })
})
