import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppShell } from './AppShell'
import { NAV_ITEMS } from '../navigation'
import { beginSave, failSave, finishSave, resetSaveStatus } from '../save-status'
import { markServiceReachable, markServiceUnreachable, resetServiceStatus } from '../service-status'

/**
 * 外壳（逐页规格 §0）的行为断言：
 * - 侧栏 200px 在 App.css 里；这里断言结构、导航 5 项、徽章、工作库行与真实的本机状态；
 * - 顶栏当前页名 + 保存三态 + 主题三选（§13.6：主题入口必须保留）。
 * 响应式（64px 图标栏 / 底部 5 栏 / 粗指针）是纯 CSS，见 App.css 与报告里的五档说明（守卫 ⑩ 仍为 todo）。
 */

const RULE_SAVE = '逐页规格 §0.2 / §5.6：顶栏保存状态必须是真实三态，不再有永远为真的「本机已保存」'
const RULE_LOCAL = '逐页规格 §0.3 / §5.6：「仅本机运行」必须反映真实的本机服务可达性（两种文案两种颜色）'

function renderShell(overrides: Partial<Parameters<typeof AppShell>[0]> = {}) {
  const props = {
    section: 'today' as const,
    onSelect: vi.fn(),
    workspaceName: '模拟工作库',
    onSwitchWorkspace: vi.fn(),
    approvalCount: 0,
    openPageTitle: null,
    themePreference: 'system' as const,
    onThemePreferenceChange: vi.fn(),
    toasts: [],
    onDismissToast: vi.fn(),
    children: <p>页面内容</p>,
    ...overrides,
  }
  return { props, ...render(<AppShell {...props} />) }
}

beforeEach(() => {
  resetSaveStatus()
  resetServiceStatus()
})

afterEach(() => {
  cleanup()
  resetSaveStatus()
  resetServiceStatus()
})

describe('侧栏（逐页规格 §0.1）', () => {
  it('主导航恰好 5 项、标签精确、顺序固定，每项有 title 与 aria-label', () => {
    renderShell()
    const nav = screen.getByRole('navigation', { name: '主导航' })
    const buttons = within(nav).getAllByRole('button')
    const labels = buttons.map((button) => button.querySelector('.nav-label')?.textContent)

    expect(buttons, '逐页规格 §0.1 / D1：主导航必须恰好 5 项，不加第 6 项').toHaveLength(5)
    expect(labels).toEqual(['今日', '审批', '项目', '知识问答', '设置'])
    expect(labels).toEqual(NAV_ITEMS.map((item) => item.label))
    for (const [index, button] of buttons.entries()) {
      expect(button.getAttribute('title')).toBe(labels[index])
      expect(button.getAttribute('aria-label')).toBe(labels[index])
    }
  })

  it('当前项带 aria-current="page"，切页后强调条与 aria-current 跟着走', () => {
    const { props, rerender } = renderShell()
    const nav = screen.getByRole('navigation', { name: '主导航' })
    const current = () => within(nav).getAllByRole('button').filter((button) => button.getAttribute('aria-current') === 'page')

    expect(current().map((button) => button.textContent)).toEqual(['今日'])
    expect(current()[0].className).toContain('active')

    rerender(<AppShell {...props} section="approval" />)
    expect(current().map((button) => button.textContent)).toEqual(['审批'])
    expect(within(nav).getByRole('button', { name: '今日' }).className).not.toContain('active')
  })

  it('审批项的数量徽章：为 0 时不显示，大于 0 时显示数量并写进可访问名', () => {
    const { props, rerender } = renderShell()
    const nav = screen.getByRole('navigation', { name: '主导航' })
    expect(within(nav).getByRole('button', { name: '审批' })).toBeTruthy()
    expect(document.querySelector('.nav-badge'), '逐页规格 §0.1：为 0 时不显示徽章').toBeNull()

    rerender(<AppShell {...props} approvalCount={7} />)
    const approval = within(nav).getByRole('button', { name: '审批，7 项待处理' })
    expect(within(approval).getByText('7')).toBeTruthy()
  })

  it('底部：工作库名 + 首字头像 + 「切换…」，没有暗示下拉的 ⌄', () => {
    const { props } = renderShell({ workspaceName: '模拟工作库' })
    const button = screen.getByRole('button', { name: '切换工作库' })
    expect(within(button).getByText('模拟工作库')).toBeTruthy()
    expect(within(button).getByText('模')).toBeTruthy()
    expect(within(button).getByText('切换…')).toBeTruthy()
    expect(document.body.textContent, '逐页规格 §0.3：不用 ⌄ 暗示不存在的下拉菜单').not.toContain('⌄')

    fireEvent.click(button)
    expect(props.onSwitchWorkspace).toHaveBeenCalledTimes(1)
  })

  it('「仅本机运行」反映真实可达性：可达 / 不可达两种文案两种颜色', () => {
    renderShell()
    const online = document.querySelector('.local-indicator') as HTMLElement
    expect(online.textContent).toBe('仅本机运行')
    expect(online.className).toContain('is-online')

    act(() => markServiceUnreachable())
    const offline = document.querySelector('.local-indicator') as HTMLElement
    expect(offline.textContent, RULE_LOCAL).toBe('本机服务未连接')
    expect(offline.className).toContain('is-offline')

    act(() => markServiceReachable())
    expect(document.querySelector('.local-indicator')?.textContent).toBe('仅本机运行')
  })
})

describe('顶栏（逐页规格 §0.2）', () => {
  it('左显示当前页名；进入页面阅读时才显示「项目 / 页面名」层级', () => {
    const { props, rerender } = renderShell({ section: 'projects' })
    expect(document.querySelector('.crumbs')?.textContent).toBe('项目')

    rerender(<AppShell {...props} section="projects" openPageTitle="会议地点" />)
    const crumbs = document.querySelector('.crumbs') as HTMLElement
    expect(crumbs.textContent).toBe('项目/会议地点')
  })

  it('删掉硬编码头像「罗」与永远为真的「本机已保存」', () => {
    renderShell()
    expect(screen.queryByRole('button', { name: '打开设置' }), '逐页规格 §0.2：删除硬编码头像「罗」').toBeNull()
    expect(document.body.textContent).not.toContain('罗')
    expect(document.body.textContent, RULE_SAVE).not.toContain('本机已保存')
  })

  it('保存三态：未保存过时不说话，保存中… → 已保存，失败后可按重试', () => {
    renderShell()
    expect(screen.queryByText('已保存'), RULE_SAVE).toBeNull()
    expect(screen.queryByText('保存中…')).toBeNull()

    const retry = vi.fn()
    act(() => beginSave(retry))
    expect(screen.getByText('保存中…')).toBeTruthy()

    act(() => finishSave())
    expect(screen.getByText('已保存')).toBeTruthy()

    act(() => beginSave(retry))
    act(() => failSave())
    const retryButton = screen.getByRole('button', { name: '保存失败，点击重试' })
    expect(retryButton).toBeTruthy()
    fireEvent.click(retryButton)
    expect(retry, '「保存失败，点击重试」必须真的重试那次写请求').toHaveBeenCalledTimes(1)
  })

  it('主题三选保留在顶栏（GUIDE §13.6）', () => {
    const { props } = renderShell()
    const select = screen.getByLabelText('主题') as HTMLSelectElement
    expect(Array.from(select.options).map((option) => option.textContent)).toEqual(['跟随系统', '浅色', '深色'])
    fireEvent.change(select, { target: { value: 'dark' } })
    expect(props.onThemePreferenceChange).toHaveBeenCalledWith('dark')
  })
})

describe('全局提示（§0.4、§5.2）', () => {
  it('常驻红色横幅已删除，提示走 toast 容器', () => {
    renderShell({ toasts: [{ id: 1, kind: 'danger', message: '保存失败，请重试。' }] })
    expect(document.querySelector('.global-alert')).toBeNull()
    expect(screen.getByRole('alert').textContent).toContain('保存失败，请重试。')
  })
})
