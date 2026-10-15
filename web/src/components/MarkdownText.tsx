import ReactMarkdown, { type Components, type Options } from 'react-markdown'
import remarkGfm from 'remark-gfm'

export type MarkdownPage = { page_id: string; content_sha256: string; title: string; relative_path: string }
type MarkdownTreeNode = { type: string; value?: string; url?: string; children?: MarkdownTreeNode[]; data?: { hProperties?: Record<string, string> } }
type PageResolverOptions = { pages: MarkdownPage[]; sourcePath?: string }

function decodePath(path: string): string | null {
  if (/%2f|%5c/i.test(path)) return null
  try { return decodeURIComponent(path) } catch { return null }
}

function normalizePath(path: string, sourcePath?: string): string | null {
  const decoded = decodePath(path)
  if (!decoded || decoded.startsWith('/') || decoded.startsWith('\\') || decoded.startsWith('//') || decoded.includes('\\')) return null
  if (decoded.includes('?') || /^[a-z][a-z\d+.-]*:/i.test(decoded)) return null
  const parts = (sourcePath ? sourcePath.split('/').slice(0, -1) : []).filter(Boolean)
  for (const segment of decoded.split('#', 1)[0].split('/')) {
    if (!segment || segment === '.') continue
    if (segment === '..') {
      if (!parts.length) return null
      parts.pop()
    } else {
      parts.push(segment)
    }
  }
  return parts.join('/') || null
}

function unique<T>(matches: T[]): T | null {
  return matches.length === 1 ? matches[0] : null
}

function resolvePage(target: string, options: PageResolverOptions): MarkdownPage | null {
  const name = target.trim()
  if (!name || name.startsWith('/') || name.startsWith('\\') || name.startsWith('//') || /^[a-z][a-z\d+.-]*:/i.test(name)) return null
  const byId = options.pages.filter((page) => page.page_id === name)
  if (byId.length) return unique(byId)
  const isPath = name.startsWith('./') || name.startsWith('../') || name.includes('/') || /\.md$/i.test(name)
  if (isPath) {
    const normalized = normalizePath(name, options.sourcePath)
    return normalized ? unique(options.pages.filter((page) => page.relative_path.replace(/^\.\//, '') === normalized)) : null
  }
  return unique(options.pages.filter((page) => page.title === name))
}

function pageProperties(page: MarkdownPage): { 'data-page-id': string; 'data-page-hash': string } {
  return { 'data-page-id': page.page_id, 'data-page-hash': page.content_sha256 }
}

function resolveLinkNode(node: MarkdownTreeNode, options: PageResolverOptions) {
  if (node.type !== 'link' || !node.url) return
  const href = node.url
  if (href.startsWith('#')) return
  if (/^https?:\/\//i.test(href) || /^mailto:/i.test(href)) return
  if (/^[a-z][a-z\d+.-]*:/i.test(href) || href.startsWith('//') || href.startsWith('\\') || href.startsWith('/')) {
    node.data = { ...node.data, hProperties: { ...node.data?.hProperties, 'data-page-link-invalid': 'true' } }
    return
  }
  const path = normalizePath(href, options.sourcePath)
  const target = path ? unique(options.pages.filter((page) => page.relative_path.replace(/^\.\//, '') === path)) : null
  if (target) node.data = { ...node.data, hProperties: { ...node.data?.hProperties, ...pageProperties(target) } }
  else node.data = { ...node.data, hProperties: { ...node.data?.hProperties, 'data-page-link-invalid': 'true' } }
}

function rewriteTextNode(node: MarkdownTreeNode, options: PageResolverOptions): MarkdownTreeNode[] {
  if (node.type !== 'text' || !node.value?.includes('[[')) return [node]
  const output: MarkdownTreeNode[] = []
  const pattern = /\[\[([^\]\n]+)\]\]/g
  let cursor = 0
  for (const match of node.value.matchAll(pattern)) {
    const index = match.index ?? 0
    if (index > cursor) output.push({ type: 'text', value: node.value.slice(cursor, index) })
    const raw = match[1].trim()
    const separator = raw.indexOf('|')
    const targetName = (separator < 0 ? raw : raw.slice(0, separator)).trim()
    const label = (separator < 0 ? '' : raw.slice(separator + 1)).trim()
    const page = resolvePage(targetName, options)
    if (page) {
      output.push({ type: 'link', url: '#', data: { hProperties: pageProperties(page) }, children: [{ type: 'text', value: label || page.title }] })
    } else {
      output.push({ type: 'link', url: '#', data: { hProperties: { 'data-page-link-invalid': 'true' } }, children: [{ type: 'text', value: label || targetName || match[0] }] })
    }
    cursor = index + match[0].length
  }
  if (cursor === 0) return [node]
  if (cursor < node.value.length) output.push({ type: 'text', value: node.value.slice(cursor) })
  return output
}

function walk(node: MarkdownTreeNode, options: PageResolverOptions) {
  if (['link', 'linkReference', 'image', 'imageReference', 'inlineCode', 'code', 'html', 'definition'].includes(node.type)) return
  if (!node.children) return
  const rewritten: MarkdownTreeNode[] = []
  for (const child of node.children) {
    if (child.type === 'text') rewritten.push(...rewriteTextNode(child, options))
    else {
      resolveLinkNode(child, options)
      walk(child, options)
      rewritten.push(child)
    }
  }
  node.children = rewritten
}

function isMarkdownNode(value: unknown): value is MarkdownTreeNode {
  return typeof value === 'object' && value !== null && 'type' in value && typeof value.type === 'string'
}

function pageResolverPlugin(options: PageResolverOptions) {
  return (tree: unknown) => { if (isMarkdownNode(tree)) walk(tree, options) }
}

export function MarkdownText({ content, onOpenPage, pageIndex = [], sourcePath, className }: {
  content: string
  onOpenPage?: (pageId: string, expectedHash: string) => void
  pageIndex?: MarkdownPage[]
  sourcePath?: string
  className?: string
}) {
  const components: Components = {
    a({ href = '', children, node: _node, ...props }) {
      const pageId = (props as Record<string, unknown>)['data-page-id']
      const pageHash = (props as Record<string, unknown>)['data-page-hash']
      const invalid = (props as Record<string, unknown>)['data-page-link-invalid'] === 'true'
      if (typeof pageId === 'string' && typeof pageHash === 'string') {
        return <a href="#" {...props} onClick={(event) => { event.preventDefault(); onOpenPage?.(pageId, pageHash) }}>{children}</a>
      }
      if (invalid) return <span className="markdown-unresolved-link" title="页面未找到、无法唯一匹配或链接格式不受支持">{children}</span>
      if (/^https?:\/\//i.test(href) || /^mailto:/i.test(href)) return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
      if (href.startsWith('#')) return <a href={href}>{children}</a>
      return <>{children}</>
    },
  }
  const plugins: NonNullable<Options['remarkPlugins']> = [remarkGfm, [pageResolverPlugin, { pages: pageIndex, sourcePath }]]
  return <div className={['markdown-content', className].filter(Boolean).join(' ')}>
    <ReactMarkdown remarkPlugins={plugins} components={components}>{content}</ReactMarkdown>
  </div>
}
