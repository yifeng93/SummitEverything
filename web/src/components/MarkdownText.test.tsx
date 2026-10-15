import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MarkdownText } from './MarkdownText'
import { StreamingMarkdown } from './StreamingMarkdown'

afterEach(cleanup)

it('renders GFM structures, routes internal links, and secures external links', () => {
  const onOpenPage = vi.fn()
  render(<MarkdownText
    onOpenPage={onOpenPage}
    content={'## 标题\n\n| 名称 | 状态 |\n| --- | --- |\n| 工作库 | 可用 |\n\n- 第一项\n- [[安全说明]]\n\n```ts\nconst answer = 42\n```\n\n[外部说明](https://example.com)'}
  />)
  expect(screen.getByRole('heading', { name: '标题' })).toBeTruthy()
  expect(screen.getByRole('table')).toBeTruthy()
  expect(screen.getByText('const answer = 42')).toBeTruthy()
  fireEvent.click(screen.getByRole('link', { name: '安全说明' }))
  expect(onOpenPage).toHaveBeenCalledWith('安全说明')
  const external = screen.getByRole('link', { name: '外部说明' })
  expect(external.getAttribute('target')).toBe('_blank')
  expect(external.getAttribute('rel')).toContain('noopener')
})

it('shows raw HTML as text and does not create executable elements', () => {
  const { container } = render(<MarkdownText content={'<img src=x onerror="alert(1)">'} />)
  expect(container.querySelector('img')).toBeNull()
  expect(container.textContent).toContain('<img src=x onerror="alert(1)">')
})

it('holds unfinished syntax while streaming and matches complete Markdown at the terminal state', () => {
  const text = '答案已完成。**还没结束'
  const streaming = render(<StreamingMarkdown content={text} />)
  expect(streaming.container.textContent).toContain('答案已完成。')
  expect(streaming.container.textContent).not.toContain('**')
  expect(streaming.container.textContent).not.toContain('还没结束')
  streaming.rerender(<StreamingMarkdown content={'答案已完成。**完整强调**'} complete />)
  const terminalHTML = streaming.container.innerHTML
  const complete = render(<MarkdownText content={'答案已完成。**完整强调**'} />)
  expect(terminalHTML).toBe(complete.container.innerHTML)
  expect(streaming.container.querySelector('[aria-live]')).toBeNull()
})

it('keeps code content once its fence is complete', () => {
  const { container, rerender } = render(<StreamingMarkdown content={'```ts\nconst value = 1'} />)
  expect(container.textContent).not.toContain('```')
  rerender(<StreamingMarkdown content={'```ts\nconst value = 1\n```'} complete />)
  expect(container.querySelector('code')?.textContent?.trimEnd()).toBe('const value = 1')
})
