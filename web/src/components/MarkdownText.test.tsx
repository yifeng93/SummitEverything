import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { MarkdownText, type MarkdownPage } from './MarkdownText'
import { StreamingMarkdown } from './StreamingMarkdown'

afterEach(cleanup)

const pages: MarkdownPage[] = [
  { page_id: 'page-1', content_sha256: 'a'.repeat(64), title: '安全说明', relative_path: 'line/project/safety.md' },
  { page_id: 'page-2', content_sha256: 'b'.repeat(64), title: '重复标题', relative_path: 'line/project/one.md' },
  { page_id: 'page-3', content_sha256: 'c'.repeat(64), title: '重复标题', relative_path: 'line/project/two.md' },
]

it('renders GFM, resolves only real unique page links, and secures external links', () => {
  const onOpenPage = vi.fn()
  render(<MarkdownText
    pageIndex={pages}
    sourcePath="line/project/source.md"
    onOpenPage={onOpenPage}
    content={'## 标题\n\n| 名称 | 状态 |\n| --- | --- |\n| 工作库 | 可用 |\n\n- [[page-1|安全说明]]\n- [相对链接](safety.md)\n- [[重复标题]]\n- [[未知页面|仍可读]]\n\n```ts\nconst answer = 42\n[[page-1]]\n```\n\n[外部说明](https://example.com)\n[危险链接](javascript:alert(1))'}
  />)
  expect(screen.getByRole('heading', { name: '标题' })).toBeTruthy()
  expect(screen.getByRole('table')).toBeTruthy()
  expect(screen.getByText(/const answer = 42[\s\S]*\[\[page-1\]\]/)).toBeTruthy()
  fireEvent.click(screen.getByRole('link', { name: '安全说明' }))
  fireEvent.click(screen.getByRole('link', { name: '相对链接' }))
  expect(onOpenPage).toHaveBeenNthCalledWith(1, 'page-1', 'a'.repeat(64))
  expect(onOpenPage).toHaveBeenNthCalledWith(2, 'page-1', 'a'.repeat(64))
  expect(screen.queryByRole('link', { name: '重复标题' })).toBeNull()
  expect(screen.getByText('重复标题', { selector: '.markdown-unresolved-link' })).toBeTruthy()
  expect(screen.getByText('仍可读')).toBeTruthy()
  const external = screen.getByRole('link', { name: '外部说明' })
  expect(external.getAttribute('target')).toBe('_blank')
  expect(external.getAttribute('rel')).toContain('noopener')
  expect(screen.queryByRole('link', { name: '危险链接' })).toBeNull()
  expect(onOpenPage).toHaveBeenCalledTimes(2)
})

it('rejects root escape, absolute, and protocol-relative Markdown targets while keeping labels readable', () => {
  render(<MarkdownText pageIndex={pages} sourcePath="line/project/source.md" content={'[[../../../outside.md|越界]]\n\n[绝对](/line/project/safety.md)\n\n[协议相对](//example.com)\n\n[坏编码](bad%ZZ.md)'} />)
  expect(screen.getByText('越界')).toBeTruthy()
  expect(screen.getByText('绝对')).toBeTruthy()
  expect(screen.getByText('协议相对')).toBeTruthy()
  expect(screen.getByText('坏编码')).toBeTruthy()
  expect(screen.queryAllByRole('link')).toHaveLength(0)
})

it('resolves reference-style internal links and keeps external references safe', () => {
  const onOpenPage = vi.fn()
  render(<MarkdownText pageIndex={pages} sourcePath="line/project/source.md" onOpenPage={onOpenPage} content={'[阅读安全说明][guide]、[外部说明][site]、[危险链接][bad]\n\n[guide]: safety.md\n[site]: https://example.com/docs\n[bad]: javascript:alert(1)'} />)
  fireEvent.click(screen.getByRole('link', { name: '阅读安全说明' }))
  expect(onOpenPage).toHaveBeenCalledWith('page-1', 'a'.repeat(64))
  const external = screen.getByRole('link', { name: '外部说明' })
  expect(external.getAttribute('href')).toBe('https://example.com/docs')
  expect(external.getAttribute('rel')).toContain('noopener')
  expect(screen.getByText('危险链接')).toBeTruthy()
  expect(screen.queryByRole('link', { name: '危险链接' })).toBeNull()
})

it('shows raw HTML as text and does not create executable elements', () => {
  const { container } = render(<MarkdownText content={'<img src=x onerror="alert(1)">'} />)
  expect(container.querySelector('img')).toBeNull()
  expect(container.textContent).toContain('<img src=x onerror="alert(1)">')
})

it('keeps every chunk of incomplete syntax visible and matches the static terminal DOM', () => {
  const completeText = '普通下划线变量_name_仍可读。**完整强调** 与 `行内代码`。\n\n| 名称 | 状态 |\n| --- | --- |\n| Alpha | 已确认 |\n\n[[page-1|相关页面]]\n\n~~~js\nconst unfinishedUntilNow = true\n~~~'
  const onOpenPage = vi.fn()
  const { container, rerender } = render(<StreamingMarkdown content="" pageIndex={pages} sourcePath="line/project/source.md" onOpenPage={onOpenPage} />)
  const chunks = [
    'ordinary_name',
    'ordinary_name **bold',
    'ordinary_name **bold** and `inline',
    'ordinary_name **bold** and `inline`\n\n~~~js\nconst code = 1',
    completeText,
  ]
  for (const chunk of chunks) {
    rerender(<StreamingMarkdown content={chunk} pageIndex={pages} sourcePath="line/project/source.md" onOpenPage={onOpenPage} />)
    if (chunk.includes('ordinary_name')) expect(container.textContent).toContain('ordinary_name')
    if (chunk.includes('bold')) expect(container.textContent).toContain('bold')
    if (chunk.includes('inline')) expect(container.textContent).toContain('inline')
    if (chunk.includes('const code')) expect(container.textContent).toContain('const code = 1')
  }
  rerender(<StreamingMarkdown content={completeText} complete pageIndex={pages} sourcePath="line/project/source.md" onOpenPage={onOpenPage} />)
  const terminalHTML = container.innerHTML
  const complete = render(<MarkdownText content={completeText} pageIndex={pages} sourcePath="line/project/source.md" onOpenPage={onOpenPage} />)
  expect(terminalHTML).toBe(complete.container.innerHTML)
  expect(container.querySelector('pre code')?.textContent).toContain('const unfinishedUntilNow = true')
  fireEvent.click(container.querySelector('a')!)
  expect(onOpenPage).toHaveBeenCalledWith('page-1', 'a'.repeat(64))
  expect(container.querySelector('[aria-live]')).toBeNull()
})
