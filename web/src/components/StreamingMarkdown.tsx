import { MarkdownText, type MarkdownPage } from './MarkdownText'

export function StreamingMarkdown({ content, onOpenPage, pageIndex, sourcePath, className }: {
  content: string
  complete?: boolean
  onOpenPage?: (pageId: string, expectedHash: string) => void
  pageIndex?: MarkdownPage[]
  sourcePath?: string
  className?: string
}) {
  // Render the exact accumulated source on every chunk; ReactMarkdown keeps incomplete
  // fences and inline syntax readable without dropping already received text.
  return <MarkdownText content={content} onOpenPage={onOpenPage} pageIndex={pageIndex} sourcePath={sourcePath} className={className} />
}
