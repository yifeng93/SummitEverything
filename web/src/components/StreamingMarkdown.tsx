import { MarkdownText, type MarkdownPage } from './MarkdownText'

type Fence = { marker: '`' | '~'; length: number }

function fenceMarker(line: string): Fence | null {
  const match = line.match(/^ {0,3}(`{3,}|~{3,})(.*)$/)
  return match ? { marker: match[1][0] as Fence['marker'], length: match[1].length } : null
}

function stabilise(source: string): string {
  const lines = source.split('\n')
  let fence: Fence | null = null
  let afterFence = 0
  let offset = 0
  for (const line of lines) {
    const marker = fenceMarker(line)
    if (fence) {
      if (marker?.marker === fence.marker && marker.length >= fence.length && /^\s*$/.test(line.slice(line.indexOf(marker.marker) + marker.length))) {
        fence = null
        afterFence = offset + line.length + 1
      }
    } else if (marker) {
      fence = marker
    }
    offset += line.length + 1
  }
  if (fence) return `${source}${source.endsWith('\n') ? '' : '\n'}${fence.marker.repeat(fence.length)}`

  let content = source
  const lastBlank = source.lastIndexOf('\n\n')
  let tailStart = Math.max(afterFence, lastBlank < 0 ? 0 : lastBlank + 2)
  let tail = content.slice(tailStart)

  // Make a trailing table render as a table without changing its cells.
  const tableLines = content.split('\n')
  let tableStart = tableLines.length - 1
  const isTableLine = (line: string) => /^\s*\|/.test(line) && (line.match(/\|/g)?.length ?? 0) >= 2
  while (tableStart >= 0 && isTableLine(tableLines[tableStart])) tableStart -= 1
  tableStart += 1
  if (tableStart < tableLines.length && tableLines.slice(tableStart).some(isTableLine)) {
    for (let index = tableStart; index < tableLines.length; index += 1) {
      if (isTableLine(tableLines[index]) && !tableLines[index].trimEnd().endsWith('|')) tableLines[index] += ' |'
    }
    if (tableStart + 1 >= tableLines.length || !/^\s*\|?\s*:?-{3,}/.test(tableLines[tableStart + 1])) {
      const columns = Math.max(1, (tableLines[tableStart].match(/\|/g)?.length ?? 2) - 1)
      tableLines.splice(tableStart + 1, 0, `| ${Array(columns).fill('---').join(' | ')} |`)
    }
    content = tableLines.join('\n')
    tail = content.slice(tailStart)
  }

  // Count code spans and incomplete links only outside escaped text and code.
  const openLinks: { kind: 'wiki' | 'label' | 'destination'; start: number; labelStart: number }[] = []
  const codeRuns: number[] = []
  let escaped = false
  for (let index = 0; index < tail.length;) {
    const char = tail[index]
    if (escaped) { escaped = false; index += 1; continue }
    if (char === '\\') { escaped = true; index += 1; continue }
    if (char === '`') {
      let end = index + 1
      while (tail[end] === '`') end += 1
      const length = end - index
      const runIndex = codeRuns.lastIndexOf(length)
      if (runIndex >= 0) codeRuns.splice(runIndex, 1)
      else codeRuns.push(length)
      index = end
      continue
    }
    if (codeRuns.length) { index += 1; continue }
    if (tail.startsWith('[[', index)) { openLinks.push({ kind: 'wiki', start: index, labelStart: index + 2 }); index += 2; continue }
    if (tail.startsWith(']]', index) && openLinks.some((link) => link.kind === 'wiki')) { openLinks.splice(openLinks.findLastIndex((link) => link.kind === 'wiki'), 1); index += 2; continue }
    if (char === '|' && openLinks.at(-1)?.kind === 'wiki') { openLinks[openLinks.length - 1].labelStart = index + 1; index += 1; continue }
    if (char === '[') { openLinks.push({ kind: 'label', start: index, labelStart: index + 1 }); index += 1; continue }
    if (char === ']' && openLinks.at(-1)?.kind === 'label') {
      if (tail[index + 1] === '(') openLinks[openLinks.length - 1].kind = 'destination'
      else openLinks.pop()
      index += 1
      continue
    }
    if (char === ')' && openLinks.at(-1)?.kind === 'destination') { openLinks.pop(); index += 1; continue }
    index += 1
  }

  if (codeRuns.length) return content + '`'.repeat(codeRuns.at(-1)!)
  const pending = openLinks.at(-1)
  if (pending?.kind === 'wiki') {
    const label = content.slice(tailStart + pending.labelStart).split('\n', 1)[0]
    content = `${content.slice(0, tailStart + pending.start)}${label}`
  } else if (pending?.kind === 'destination') {
    const label = content.slice(tailStart + pending.labelStart, content.lastIndexOf(']('))
    content = `${content.slice(0, tailStart + pending.start)}${label}`
  } else if (pending?.kind === 'label') {
    const label = content.slice(tailStart + pending.labelStart).split('\n', 1)[0]
    content = `${content.slice(0, tailStart + pending.start)}${label}`
  }

  tailStart = Math.max(afterFence, lastBlank < 0 ? 0 : lastBlank + 2)
  tail = content.slice(tailStart)
  const emphasis: string[] = []
  escaped = false
  for (let index = 0; index < tail.length;) {
    const char = tail[index]
    if (escaped) { escaped = false; index += 1; continue }
    if (char === '\\') { escaped = true; index += 1; continue }
    if (char === '`') {
      let end = index + 1
      while (tail[end] === '`') end += 1
      const closing = tail.indexOf('`'.repeat(end - index), end)
      index = closing < 0 ? tail.length : closing + (end - index)
      continue
    }
    const marker = tail.startsWith('**', index) ? '**' : tail.startsWith('~~', index) ? '~~' : char === '*' ? '*' : ''
    if (!marker) { index += 1; continue }
    let end = index + marker.length
    while (tail.slice(end, end + marker.length) === marker) end += marker.length
    const previous = tail[index - 1]
    const next = tail[end]
    const canOpen = next !== undefined && !/\s/.test(next) && (previous === undefined || /\s|[([{—–-]/.test(previous))
    const canClose = previous !== undefined && !/\s/.test(previous) && (next === undefined || /\s|[.,!?;:)}\]—–-]/.test(next))
    if (canClose && emphasis.at(-1) === marker) emphasis.pop()
    else if (canOpen) emphasis.push(marker)
    index = end
  }
  for (const marker of emphasis.reverse()) content += marker
  return content
}

export function StreamingMarkdown({ content, complete = false, onOpenPage, pageIndex, sourcePath, className }: {
  content: string
  complete?: boolean
  onOpenPage?: (pageId: string, expectedHash: string) => void
  pageIndex?: MarkdownPage[]
  sourcePath?: string
  className?: string
}) {
  const preview = complete ? content : stabilise(content)
  return <MarkdownText content={preview} onOpenPage={onOpenPage} pageIndex={pageIndex} sourcePath={sourcePath} className={className} />
}
