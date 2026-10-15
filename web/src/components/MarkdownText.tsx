import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

function transformWikilinks(markdown: string): string {
  let inFence = false
  return markdown.split('\n').map((line) => {
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence
      return line
    }
    if (inFence) return line
    return line.replace(/(?<!`)\[\[([^\]\n]+)\]\](?!`)/g, (_match, title: string) => {
      const label = title.trim()
      return `[${label}](https://summit.local/page/${encodeURIComponent(label)})`
    })
  }).join('\n')
}

export function MarkdownText({ content, onOpenPage }: { content: string; onOpenPage?: (title: string) => void }) {
  const components: Components = {
    a({ href = '', children, node: _node, ...props }) {
      const internalPrefix = 'https://summit.local/page/'
      if (href.startsWith(internalPrefix)) {
        const title = decodeURIComponent(href.slice(internalPrefix.length))
        return <a href={href} {...props} onClick={(event) => { event.preventDefault(); onOpenPage?.(title) }}>{children}</a>
      }
      return <a href={href} target="_blank" rel="noopener noreferrer" {...props}>{children}</a>
    },
  }

  return <div className="markdown-content">
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{transformWikilinks(content)}</ReactMarkdown>
  </div>
}
