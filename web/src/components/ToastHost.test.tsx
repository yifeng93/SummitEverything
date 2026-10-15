import { act, cleanup, fireEvent, render, renderHook, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ToastHost } from './ToastHost'
import { TOAST_LIMIT, useToasts, type Toast } from '../toast'

/**
 * 全局提示（FRONTEND-GUIDE §5.2、D9）：
 * 三色、最多 3 条、成功自动消失、失败不自动消失且可手关。
 */

const RULE_FAILURE_PERSISTS = 'GUIDE §5.2：失败提示不自动消失，必须由用户手关'

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

function toast(kind: Toast['kind'], id = 1, message = '一条提示'): Toast {
  return { id, kind, message }
}

describe('toast 三色与可访问性', () => {
  it('成功/失败/中性三色分别渲染，失败用 role="alert"、其余用 role="status"', () => {
    render(<ToastHost toasts={[toast('success', 1, '已保存到本机。'), toast('danger', 2, '保存失败。'), toast('neutral', 3, '已取消，没有发送。')]} onDismiss={vi.fn()} />)
    expect(screen.getByText('已保存到本机。').closest('.toast')?.className).toContain('toast-success')
    expect(screen.getByText('保存失败。').closest('.toast')?.className).toContain('toast-danger')
    expect(screen.getByText('已取消，没有发送。').closest('.toast')?.className).toContain('toast-neutral')
    expect(screen.getByRole('alert').textContent).toContain('保存失败。')
    expect(screen.getAllByRole('status').map((node) => node.querySelector('.toast-message')?.textContent))
      .toEqual(['已保存到本机。', '已取消，没有发送。'])
  })

  it('关闭按钮有可访问名，点击后回调该条 id', () => {
    const onDismiss = vi.fn()
    render(<ToastHost toasts={[toast('danger', 9, '保存失败。')]} onDismiss={onDismiss} />)
    const close = screen.getByRole('button', { name: '关闭这条提示' })
    expect(close.getAttribute('title')).toBe('关闭这条提示')
    fireEvent.click(close)
    expect(onDismiss).toHaveBeenCalledWith(9)
  })

  it('没有提示时不渲染容器', () => {
    const { container } = render(<ToastHost toasts={[]} onDismiss={vi.fn()} />)
    expect(container.querySelector('.toast-region')).toBeNull()
  })
})

describe('toast 生命周期', () => {
  it('成功 3.5s 后自动消失，中性 5s 后自动消失', () => {
    vi.useFakeTimers()
    const onDismiss = vi.fn()
    render(<ToastHost toasts={[toast('success', 1, '已保存。'), toast('neutral', 2, '已取消。')]} onDismiss={onDismiss} />)

    act(() => { vi.advanceTimersByTime(3400) })
    expect(onDismiss).not.toHaveBeenCalled()
    act(() => { vi.advanceTimersByTime(200) })
    expect(onDismiss).toHaveBeenCalledWith(1)

    act(() => { vi.advanceTimersByTime(1500) })
    expect(onDismiss).toHaveBeenCalledWith(2)
  })

  it('失败提示不自动消失', () => {
    vi.useFakeTimers()
    const onDismiss = vi.fn()
    render(<ToastHost toasts={[toast('danger', 3, '保存失败。')]} onDismiss={onDismiss} />)

    act(() => { vi.advanceTimersByTime(60_000) })
    expect(onDismiss, RULE_FAILURE_PERSISTS).not.toHaveBeenCalled()
  })
})

describe('useToasts', () => {
  it('同屏最多 3 条，超出的挤掉最旧一条', () => {
    const { result } = renderHook(() => useToasts())
    act(() => { result.current.notify('第一条'); result.current.notify('第二条'); result.current.notify('第三条'); result.current.notify('第四条') })
    expect(result.current.toasts).toHaveLength(TOAST_LIMIT)
    expect(result.current.toasts.map((item) => item.message)).toEqual(['第二条', '第三条', '第四条'])
  })

  it('空文案被忽略；连续重复的同一条不堆叠', () => {
    const { result } = renderHook(() => useToasts())
    act(() => { result.current.notify('   ') })
    expect(result.current.toasts).toEqual([])

    act(() => { result.current.notify('保存失败。'); result.current.notify('保存失败。') })
    expect(result.current.toasts).toHaveLength(1)
    expect(result.current.toasts[0].message).toBe('保存失败。')
  })

  it('dismiss 只移除对应的一条', () => {
    const { result } = renderHook(() => useToasts())
    act(() => { result.current.notify('第一条', 'neutral'); result.current.notify('第二条') })
    const first = result.current.toasts[0].id
    act(() => result.current.dismiss(first))
    expect(result.current.toasts.map((item) => item.message)).toEqual(['第二条'])
  })
})
