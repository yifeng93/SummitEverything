import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { PageDirectoryEntry } from '../api/client'
import { buildPageTree, findPageTrail, type PageTreeNode } from '../page-groups'

type Props = {
  pages: PageDirectoryEntry[]
  currentPageId: string
  heading: string
  loading?: boolean
  onOpenPage: (pageId: string, expectedHash: string) => void
}

/**
 * 阅读页的项目目录：文件夹可以多层嵌套，页面挂在所属文件夹下。
 *
 * 只负责定位与切换，不显示 ID、路径或索引细节。当前页所在的整条路径默认展开，
 * 其余保持收起，避免 150+ 页把目录撑成一整屏。
 */
export function PageTree({ pages, currentPageId, heading, loading = false, onOpenPage }: Props) {
  const tree = useMemo(() => buildPageTree(pages), [pages])
  const trail = useMemo(() => findPageTrail(tree, currentPageId), [tree, currentPageId])
  const trailKey = (trail ?? []).map((node) => node.key).join('|')
  const [open, setOpen] = useState<Set<string>>(() => new Set(trailKey ? trailKey.split('|') : []))

  useEffect(() => {
    if (!trailKey) return
    const keys = trailKey.split('|')
    setOpen((current) => {
      const next = new Set(current)
      let changed = false
      for (const key of keys) if (!next.has(key)) { next.add(key); changed = true }
      return changed ? next : current
    })
  }, [trailKey])

  function toggle(key: string) {
    setOpen((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  function renderNode(node: PageTreeNode) {
    const expanded = open.has(node.key)
    return <li key={node.key}>
      <button className="page-tree-node" aria-expanded={expanded} title={node.label} onClick={() => toggle(node.key)}>
        {expanded ? <ChevronDown size={13} strokeWidth={2} aria-hidden="true" /> : <ChevronRight size={13} strokeWidth={2} aria-hidden="true" />}
        <span className="page-tree-label">{node.label}</span>
        <span className="page-tree-count">{node.total}</span>
      </button>
      {expanded && <ul className="page-tree-list">
        {node.children.map((child) => renderNode(child))}
        {node.pages.map((page) => {
          const current = page.page_id === currentPageId
          return <li key={page.page_id}>
            <button
              className="page-tree-page"
              aria-current={current ? 'page' : undefined}
              title={String(page.metadata.title ?? '未命名页面')}
              onClick={() => { if (!current) onOpenPage(page.page_id, page.content_sha256) }}
            >{String(page.metadata.title ?? '未命名页面')}</button>
          </li>
        })}
      </ul>}
    </li>
  }

  return <nav className="page-tree" aria-label="知识目录">
    <p className="page-tree-heading">{heading}</p>
    {loading && pages.length === 0 && <p className="page-tree-empty">正在读取目录…</p>}
    {!loading && pages.length === 0 && <p className="page-tree-empty">这个项目还没有其他页面。</p>}
    {tree.length > 0 && <ul className="page-tree-list">{tree.map((node) => renderNode(node))}</ul>}
  </nav>
}
