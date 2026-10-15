/**
 * 机器守卫 · 组件渲染（FRONTEND-GUIDE §11）。
 *
 * 本文件本轮实现并做变异验证：
 *   ① 渲染出的 DOM 里不得有内联样式裸色（与 ui-contract.test.ts 的源码扫描互补）
 *   B 深色一等公民 —— 主题三选在运行期写 <html data-theme> 并持久化（§5.6、§6.2）
 * 其余渲染类守卫以 it.todo 登记归属切片（不得当成已通过）。
 */
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import App from './App'
import { DARK_MEDIA_QUERY, THEME_STORAGE_KEY } from './theme'

const RULE_BARE_COLOR = '守卫① 裸色（GUIDE §11 ① 与 §6.1）：渲染出的内联样式不得出现裸 hex / rgb / hsl'
const RULE_THEME = '深色一等公民（GUIDE §5.6 与 §6.2）：主题三选必须在运行期写入 <html data-theme> 并持久化到 localStorage'

const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/

const workspace = {
  workspace_id: 'workspace-1',
  root: '/tmp/workspace',
  local_profile_dir: '/tmp/profile',
  name: '测试工作库',
  read_only: false,
}

function stubShell(): void {
  const rawFetch = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url === '/api/v1/workspaces/current') return Response.json(workspace)
    if (url === '/api/v1/today' || url === '/api/v1/journal') return Response.json({ items: [] })
    if (url === '/api/v1/intake/items' || url === '/api/v1/drafts' || url === '/api/v1/actions'
      || url === '/api/v1/lines' || url === '/api/v1/projects' || url === '/api/v1/pages') return Response.json([])
    throw new Error(`Unexpected fetch ${url}`)
  })
  vi.stubGlobal('fetch', rawFetch)
}

function stubSystemPrefersDark(matches: boolean): void {
  vi.stubGlobal('matchMedia', vi.fn((query: string) => ({
    matches: query === DARK_MEDIA_QUERY ? matches : false,
    media: query,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  })))
}

beforeEach(() => {
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
  window.localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
})

it('渲染出的 DOM 里没有内联样式的裸色（GUIDE §11 ①）', async () => {
  stubShell()
  render(<App />)
  await screen.findByLabelText('主题')

  const offenders = Array.from(document.querySelectorAll<HTMLElement>('[style]'))
    .map((element) => ({ tag: element.tagName.toLowerCase(), style: element.getAttribute('style') ?? '' }))
    .filter((entry) => COLOR_LITERAL.test(entry.style))
    .map((entry) => `<${entry.tag} style="${entry.style}">`)
  const styledBlocks = Array.from(document.querySelectorAll('style'))
    .map((element) => element.textContent ?? '')
    .filter((text) => COLOR_LITERAL.test(text))

  expect(offenders, RULE_BARE_COLOR).toEqual([])
  expect(styledBlocks, RULE_BARE_COLOR).toEqual([])
})

it('主题三选：切换写入 <html data-theme> 并持久化（浅色 / 深色）', async () => {
  stubShell()
  render(<App />)
  const select = await screen.findByLabelText('主题')

  fireEvent.change(select, { target: { value: 'dark' } })
  await waitFor(() => expect(document.documentElement.dataset.theme, RULE_THEME).toBe('dark'))
  expect(window.localStorage.getItem(THEME_STORAGE_KEY), RULE_THEME).toBe('dark')

  fireEvent.change(select, { target: { value: 'light' } })
  await waitFor(() => expect(document.documentElement.dataset.theme, RULE_THEME).toBe('light'))
  expect(window.localStorage.getItem(THEME_STORAGE_KEY), RULE_THEME).toBe('light')
})

it('跟随系统：偏好 system 时按系统偏好解析 data-theme', async () => {
  stubSystemPrefersDark(true)
  window.localStorage.setItem(THEME_STORAGE_KEY, 'system')
  stubShell()
  render(<App />)

  await screen.findByLabelText('主题')
  await waitFor(() => expect(document.documentElement.dataset.theme, RULE_THEME).toBe('dark'))
  expect(window.localStorage.getItem(THEME_STORAGE_KEY), RULE_THEME).toBe('system')
})

// ── 本轮不实现，登记归属切片（禁止当成通过）───────────────────────────────────
it.todo('② 中文优先：渲染含英文 ID 的项目/主线，可见文本含中文名且不含 ID，ID 能在某个 title 里找到 —— 归属 P4 · 项目与问答（需要项目页）')
it.todo('④ 加载与空分离：对今日/审批/项目/问答 mock 永不 resolve 的 fetch，断言出现「正在读取…」且不出现空态文案 —— 归属 P3 · 信息架构（需要四个视图）')
it.todo('⑤ 删除/断开类动作必须确认：点击后出现 role="dialog" 且 API 未被调用，确认后恰好 1 次 —— 归属 P3/P4（需要页面实现确认弹层）')
it.todo('⑥ Markdown 渲染与流式容错：断言输出含 <strong>/标题/<table>，可见文本不含 ** / [[，三分块流式中间态不出现未闭合标记 —— 归属 P2 · 阅读与流式（含 react-markdown + remark-gfm 新依赖）')
it.todo('⑧ 页面区块数量与顺序：导航恰好 5 项、今日 2 工具 3 内容区且顺序为会议→待办→需要行动、设置 3 张卡、今日不含已退役内容 —— 归属 P1 · 壳与导航 / P3 · 信息架构（需要外壳与各页）')
it.todo('⑨ 列表渲染不得调用模型：渲染今日/审批/项目/问答时对 /acceptance-plans、/intake/jobs、/index/plans 的调用次数为 0 —— 归属 P3/P4（需要视图）')
