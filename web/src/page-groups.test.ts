import { describe, expect, it } from 'vitest'
import type { Page } from './api/client'
import { buildPageTree, findPageTrail, relativeDirLabel, subtreePages } from './page-groups'

function page(id: string, sourcePath?: string): Page {
  return {
    page_id: id,
    relative_path: `项目/${id}.md`,
    metadata: { title: id, kind: 'topic', ...(sourcePath ? { source_path: sourcePath } : {}) },
    body: '',
    content_sha256: 'a'.repeat(64),
    storage_area: 'formal',
    approval_state: 'confirmed',
    validity: 'current',
  }
}

describe('页面目录树', () => {
  it('保留多层文件夹，不把 docs/user/develop/basic 压成与 subsystems 平级的 basic', () => {
    const tree = buildPageTree([
      page('slots', 'docs/subsystems/slots.md'),
      page('team', 'docs/subsystems/agent-team.md'),
      page('basic-intro', 'docs/user/develop/basic/intro.md'),
      page('basic-more', 'docs/user/develop/basic/more.md'),
      page('guide', 'docs/user/guide/start.md'),
      page('root-page', 'docs/overview.md'),
    ])

    // 单一文档根被提上来：docs 自己的页面叫「总览」，其余按页面数排列。
    expect(tree.map((node) => node.label)).toEqual(['使用', '子系统', '总览'])

    const user = tree.find((node) => node.label === '使用')!
    expect(user.total).toBe(3)
    expect(user.pages).toHaveLength(0)
    expect(user.children.map((node) => node.label)).toEqual(['develop', '指南'])

    const develop = user.children[0]
    expect(develop.total).toBe(2)
    expect(develop.children.map((node) => node.label)).toEqual(['basic'])
    expect(develop.children[0].pages.map((item) => item.page_id)).toEqual(['basic-intro', 'basic-more'])
  })

  it('子树页面包含所有层级，面包屑能定位到最深一层', () => {
    const deep = page('basic-intro', 'docs/user/develop/basic/intro.md')
    const tree = buildPageTree([deep, page('slots', 'docs/subsystems/slots.md')])
    const user = tree.find((node) => node.label === '使用')!

    expect(subtreePages(user).map((item) => item.page_id)).toEqual(['basic-intro'])
    expect(findPageTrail(tree, 'basic-intro')?.map((node) => node.label)).toEqual(['使用', 'develop', 'basic'])
    expect(relativeDirLabel(deep, user)).toBe('develop / basic')
    expect(relativeDirLabel(deep, tree.find((node) => node.label === '子系统')!)).toBe('')
  })

  it('单一文档根下还有散页时，仍然把子目录提上来，不让根节点吞掉整棵树', () => {
    const tree = buildPageTree([
      page('slots', 'docs/subsystems/slots.md'),
      page('readme', 'docs/overview.md'),
      page('loose', 'README.md'),
    ])

    const totals = Object.fromEntries(tree.map((node) => [node.label, node.total]))
    expect(totals).toEqual({ 子系统: 1, 总览: 1, 根目录: 1 })
    // 「总览」只能是根目录自己的页面，不能变成 3 篇的整树父节点。
    expect(tree.some((node) => node.total === 3)).toBe(false)
  })

  it('没有来源路径的页面单独成组，不与文件夹混排', () => {
    const tree = buildPageTree([page('loose'), page('slots', 'docs/subsystems/slots.md')])
    expect(tree.map((node) => node.label)).toEqual(['子系统', '其他页面'])
    expect(tree[1].pages.map((item) => item.page_id)).toEqual(['loose'])
  })
})
