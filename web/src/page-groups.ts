import type { PageDirectoryEntry } from './api/client'

/**
 * 页面目录：从 `source_path` 还原真实的文件夹层级。
 *
 * 之前按「最后一段目录」分组，`docs/user/develop/basic` 会被压成 `basic`，
 * 和 `docs/subsystems` 平级——多层项目直接错乱。这里建真正的树：
 * 分类 = 路径段，节点带直接页面与子树页面；单一文档根（如 `docs/`）会把
 * 它的子目录提到顶层，根自己的页面仍叫「总览」。
 */
export const SOURCE_GROUP_LABELS: Record<string, string> = {
  docs: '总览',
  user: '使用',
  cookbook: '手册',
  subsystems: '子系统',
  architecture: '架构',
  development: '开发',
  guide: '指南',
}

export function pageKindLabel(page: PageDirectoryEntry): string {
  const kind = page.metadata.kind
  if (kind === 'journal') return '推进日志'
  if (kind === 'meeting') return '关联会议'
  if (kind === 'topic') return '主题'
  if (kind === 'fact') return '事实'
  return '其他页面'
}

export type PageTreeNode = {
  /** 完整目录路径，用作稳定 key；合成节点用 `__` 前缀。 */
  key: string
  label: string
  /** 直接放在这个目录里的页面。 */
  pages: PageDirectoryEntry[]
  children: PageTreeNode[]
  /** 本节点 + 所有子孙的页面数。 */
  total: number
}

type DraftNode = { key: string; label: string; pages: PageDirectoryEntry[]; children: Map<string, DraftNode> }

function dirSegments(page: PageDirectoryEntry): string[] {
  const source = page.metadata.source_path
  if (typeof source !== 'string' || !source.trim()) return []
  return source.split('/').filter(Boolean).slice(0, -1)
}

function labelOf(segment: string): string {
  return SOURCE_GROUP_LABELS[segment] ?? segment
}

function bySizeThenName(a: { total: number; label: string }, b: { total: number; label: string }): number {
  return b.total - a.total || a.label.localeCompare(b.label, 'zh-CN')
}

function finalize(node: DraftNode): PageTreeNode {
  const children = [...node.children.values()].map(finalize).sort(bySizeThenName)
  return {
    key: node.key,
    label: labelOf(node.label),
    pages: node.pages,
    children,
    total: node.pages.length + children.reduce((sum, child) => sum + child.total, 0),
  }
}

/**
 * 顶层节点：
 * - 只有一个文档根（导入通常是 `docs/`）时，把它的子目录提上来，根自己的页面单独成「总览」；
 * - 多个文档根时按根展示，不合并不同来源；
 * - 没有 `source_path` 的页面统一进「其他页面」，不与文件夹混排。
 */
export function buildPageTree(pages: PageDirectoryEntry[]): PageTreeNode[] {
  const root: DraftNode = { key: '', label: '', pages: [], children: new Map() }
  const loose: PageDirectoryEntry[] = []

  for (const page of pages) {
    const segments = dirSegments(page)
    if (!segments.length) {
      if (typeof page.metadata.source_path === 'string' && page.metadata.source_path.trim()) root.pages.push(page)
      else loose.push(page)
      continue
    }
    let cursor = root
    segments.forEach((segment, index) => {
      let child = cursor.children.get(segment)
      if (!child) {
        child = { key: segments.slice(0, index + 1).join('/'), label: segment, pages: [], children: new Map() }
        cursor.children.set(segment, child)
      }
      cursor = child
    })
    cursor.pages.push(page)
  }

  const roots = [...root.children.values()].sort((a, b) => b.pages.length - a.pages.length || a.label.localeCompare(b.label, 'zh-CN'))
  const top: PageTreeNode[] = []

  // 单一文档根（导入通常是 docs/）：把它的子目录提上来，根自己的页面单独成「总览」。
  // 注意：根下可能还有没有目录的散页（README 等），它们进「根目录」，不影响提升。
  if (roots.length === 1) {
    const only = roots[0]
    const promoted: PageTreeNode[] = [...only.children.values()].map(finalize)
    if (only.pages.length) {
      promoted.push({ key: only.key, label: labelOf(only.label), pages: only.pages, children: [], total: only.pages.length })
    }
    top.push(...promoted.sort(bySizeThenName))
  } else {
    for (const node of roots) top.push(finalize(node))
  }

  if (root.pages.length) {
    top.push({ key: '__root', label: '根目录', pages: root.pages, children: [], total: root.pages.length })
  }
  if (loose.length) {
    top.push({ key: '__loose', label: '其他页面', pages: loose, children: [], total: loose.length })
  }
  return top
}

/** 子树里的全部页面；用于「点文件夹看这一支下的所有页面」。 */
export function subtreePages(node: PageTreeNode): PageDirectoryEntry[] {
  return [...node.pages, ...node.children.flatMap(subtreePages)]
}

/** 从树里找出某个页面所在的路径（用于面包屑与默认展开）。 */
export function findPageTrail(nodes: PageTreeNode[], pageId: string, trail: PageTreeNode[] = []): PageTreeNode[] | null {
  for (const node of nodes) {
    if (node.pages.some((page) => page.page_id === pageId)) return [...trail, node]
    const found = findPageTrail(node.children, pageId, [...trail, node])
    if (found) return found
  }
  return null
}

/** 按 key 找节点；用于项目页记住当前选中的文件夹。 */
export function findNodeByKey(nodes: PageTreeNode[], key: string): PageTreeNode | null {
  for (const node of nodes) {
    if (node.key === key) return node
    const found = findNodeByKey(node.children, key)
    if (found) return found
  }
  return null
}

/** 页面相对某个节点多出来的子目录（列表行里标出来源子目录）；不在同一支时为空。 */
export function relativeDirLabel(page: PageDirectoryEntry, node: PageTreeNode): string {
  const segments = dirSegments(page)
  const nodeSegments = node.key && !node.key.startsWith('__') ? node.key.split('/') : []
  const sameBranch = nodeSegments.every((segment, index) => segments[index] === segment)
  if (!sameBranch) return ''
  return segments.slice(nodeSegments.length).map(labelOf).join(' / ')
}
