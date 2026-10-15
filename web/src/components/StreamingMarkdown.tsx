import { MarkdownText } from './MarkdownText'

function stablePrefix(source: string): string {
  const lines = source.split('\n')
  let openFenceStart = -1
  let stableLines: string[] = []

  for (const [index, line] of lines.entries()) {
    if (/^\s*(```|~~~)/.test(line)) {
      openFenceStart = openFenceStart === -1 ? index : -1
      stableLines.push(line)
      continue
    }
    if (openFenceStart !== -1) {
      stableLines.push(line)
      continue
    }
    const tail = line.match(/(?:\*\*|__|~~|\*|_|`|\x5b[^\x5d]*)[^*_~`\x5b]*$/)?.[0]
    if (tail && (tail.startsWith('**') || tail.startsWith('__') || tail.startsWith('~~') || tail.startsWith('*') || tail.startsWith('_') || tail.startsWith('`') || tail.startsWith('['))) {
      stableLines.push(line.slice(0, line.length - tail.length))
      return stableLines.join('\n')
    }
    stableLines.push(line)
  }

  return openFenceStart === -1 ? stableLines.join('\n') : lines.slice(0, openFenceStart).join('\n')
}

export function StreamingMarkdown({ content, complete = false, onOpenPage }: {
  content: string
  complete?: boolean
  onOpenPage?: (title: string) => void
}) {
  return <MarkdownText content={complete ? content : stablePrefix(content)} onOpenPage={onOpenPage} />
}
