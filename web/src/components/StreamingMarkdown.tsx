import { MarkdownText } from './MarkdownText'

function stablePrefix(source: string): string {
  const lines = source.split('\n')
  let fenceOpen = false
  let stableLines: string[] = []

  for (const line of lines) {
    if (/^\s*(```|~~~)/.test(line)) {
      fenceOpen = !fenceOpen
      stableLines.push(line)
      continue
    }
    if (fenceOpen) {
      stableLines.push(line)
      continue
    }
    const tail = line.match(/(?:\*\*|__|~~|\*|_|`|\[[^\]]*)[^*_~`\[]*$/)?.[0]
    if (tail && (tail.startsWith('**') || tail.startsWith('__') || tail.startsWith('~~') || tail.startsWith('*') || tail.startsWith('_') || tail.startsWith('`') || tail.startsWith('['))) {
      stableLines.push(line.slice(0, line.length - tail.length))
      return stableLines.join('\n')
    }
    stableLines.push(line)
  }

  return fenceOpen ? stableLines.slice(0, stableLines.findIndex((line) => /^\s*(```|~~~)/.test(line))).join('\n') : stableLines.join('\n')
}

export function StreamingMarkdown({ content, complete = false, onOpenPage }: {
  content: string
  complete?: boolean
  onOpenPage?: (title: string) => void
}) {
  return <MarkdownText content={complete ? content : stablePrefix(content)} onOpenPage={onOpenPage} />
}
