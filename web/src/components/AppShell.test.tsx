import { act, cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppShell } from './AppShell'
import { NAV_ITEMS } from '../navigation'
import { beginSave, failSave, finishSave, resetSaveStatus } from '../save-status'
import { resetServiceStatus } from '../service-status'

/**
 * 外壳（逐页规格 §0）的行为断言：
 * - 侧栏 200px 在 App.css 里；这里断言结构、导航 5 项、徽章、工作库行与外观入口；
 * - 顶栏当前页名 + 保存三态；主题三选在侧栏左下角的「外观」弹出层。
 * 响应式（64px 图标栏 / 底部 5 栏 / 粗指针）是纯 CSS，见 App.css 与报告里的五档说明（守卫 ⑩ 仍为 todo）。
 */

const RULE_SAVE = '逐页规格 §0.2 / §5.6：保存状态必须是真实三态（现位于侧栏底部），不再有永远为真的「本机已保存」'

function renderShell(overrides: Partial<Parameters<typeof AppShell>[0]> = {}) {
  const props = {
    section: 'today' as const,
    onSelect: vi.fn(),
    workspaceName: '模拟工作库',
    onSwitchWorkspace: vi.fn(),
    approvalCount: 0,
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
    // 只数一级项；「项目」下的二级快捷入口不是第 6 个目的地。
    const buttons = Array.from(nav.querySelectorAll<HTMLButtonElement>('.nav-item'))
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
    const current = () => Array.from(nav.querySelectorAll<HTMLButtonElement>('.nav-item')).filter((button) => button.getAttribute('aria-current') === 'page')

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

  it('「项目」下的二级入口显示项目名、直接回调并高亮当前项目，且不占第 6 个导航项', () => {
    const onOpenProject = vi.fn()
    const { props, rerender } = renderShell({
      section: 'projects',
      projects: [{ id: 'project-1', name: '官方文档' }, { id: 'project-2', name: '书法首客' }],
      activeProjectId: 'project-2',
      onOpenProject,
    })
    const nav = screen.getByRole('navigation', { name: '主导航' })
    expect(nav.querySelectorAll('.nav-item'), '二级项不是第 6 个目的地').toHaveLength(5)

    const shortcuts = within(nav).getByRole('list', { name: '项目快捷入口' })
    const items = within(shortcuts).getAllByRole('button')
    expect(items.map((item) => item.textContent)).toEqual(['官方文档', '书法首客'])
    expect(items[1].getAttribute('aria-current')).toBe('page')
    expect(items[0].getAttribute('aria-current')).toBeNull()

    fireEvent.click(items[0])
    expect(onOpenProject).toHaveBeenCalledWith('project-1')

    rerender(<AppShell {...props} projects={[]} />)
    expect(screen.queryByRole('list', { name: '项目快捷入口' })).toBeNull()
  })

  it('底部：紧凑工作库选择器，切换动作收进菜单', () => {
    const { props } = renderShell({ workspaceName: '模拟工作库' })
    const trigger = screen.getByRole('button', { name: '工作库：模拟工作库，打开菜单' })
    expect(within(trigger).getByText('模拟工作库')).toBeTruthy()
    expect(within(trigger).getByText('模')).toBeTruthy()
    expect(screen.queryByText('切换…')).toBeNull()

    fireEvent.click(trigger)
    const menu = screen.getByRole('dialog', { name: '工作库菜单' })
    fireEvent.click(within(menu).getByRole('button', { name: '切换工作库' }))
    expect(props.onSwitchWorkspace).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('dialog', { name: '工作库菜单' })).toBeNull()
  })

})

describe('外壳状态位（逐页规格 §0.2）', () => {
  it('不再有顶栏：页名由各页 h1 承担，不重复一条 62px 的条', () => {
    renderShell({ section: 'projects' })
    expect(document.querySelector('.topbar'), '外壳不再渲染顶栏（ADR 0025）').toBeNull()
    expect(document.querySelector('.crumbs')).toBeNull()
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

  it('主题三选保留在左下角弹出层（GUIDE §6.2）', () => {
    const { props } = renderShell()
    expect(screen.queryByLabelText('主题')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: '外观与主题' }))
    const dialog = screen.getByRole('dialog', { name: '外观与主题' })
    expect(within(dialog).getAllByRole('button').map((button) => button.textContent)).toEqual(['跟随系统', '浅色', '深色'])
    fireEvent.click(within(dialog).getByRole('button', { name: '深色' }))
    expect(props.onThemePreferenceChange).toHaveBeenCalledWith('dark')
    expect(screen.queryByRole('dialog', { name: '外观与主题' })).toBeNull()
  })
})

describe('全局提示（§0.4、§5.2）', () => {
  it('常驻红色横幅已删除，提示走 toast 容器', () => {
    renderShell({ toasts: [{ id: 1, kind: 'danger', message: '保存失败，请重试。' }] })
    expect(document.querySelector('.global-alert')).toBeNull()
    expect(screen.getByRole('alert').textContent).toContain('保存失败，请重试。')
  })
})
