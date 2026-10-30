import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { JournalDialog } from './JournalDialog'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function stubJournalFetch(save: () => Promise<unknown>) {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input)
    if (url.endsWith('/lines') || url.endsWith('/projects') || url.endsWith('/pages')) return Response.json([])
    if (url.endsWith('/journal/log')) return save()
    throw new Error(`Unexpected request ${url}`)
  }))
}

it('closes after a successful save and sends the receipt to the outer toast', async () => {
  stubJournalFetch(async () => Response.json({ saved_locally: true, index_update: 'updated' }, { status: 201 }))
  const onClose = vi.fn()
  const onError = vi.fn()
  render(<JournalDialog onClose={onClose} onError={onError} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('标题'), { target: { value: '模拟标题' } })
  fireEvent.change(screen.getByLabelText('正文'), { target: { value: '模拟正文' } })
  fireEvent.click(screen.getByRole('button', { name: '确认并保存在本机' }))
  await waitFor(() => expect(onClose).toHaveBeenCalledOnce())
  expect(onError).toHaveBeenCalledWith('本机索引已更新。', 'success')
})

it('keeps the dialog and input open when persistence fails', async () => {
  stubJournalFetch(async () => { throw new Error('保存失败') })
  const onClose = vi.fn()
  const onError = vi.fn()
  render(<JournalDialog onClose={onClose} onError={onError} onOpenPage={vi.fn()} />)
  const title = await screen.findByLabelText('标题') as HTMLInputElement
  const body = screen.getByLabelText('正文') as HTMLTextAreaElement
  fireEvent.change(title, { target: { value: '未保存标题' } })
  fireEvent.change(body, { target: { value: '未保存正文' } })
  fireEvent.click(screen.getByRole('button', { name: '确认并保存在本机' }))
  await waitFor(() => expect(onError).toHaveBeenCalledWith('保存失败'))
  expect(onClose).not.toHaveBeenCalled()
  expect(title.value).toBe('未保存标题')
  expect(body.value).toBe('未保存正文')
})

it('closes after persistence but preserves an index update warning in the outer toast', async () => {
  stubJournalFetch(async () => Response.json({ saved_locally: true, index_update: 'update_failed' }, { status: 201 }))
  const onClose = vi.fn()
  const onError = vi.fn()
  render(<JournalDialog onClose={onClose} onError={onError} onOpenPage={vi.fn()} />)
  fireEvent.change(await screen.findByLabelText('标题'), { target: { value: '模拟标题' } })
  fireEvent.change(screen.getByLabelText('正文'), { target: { value: '模拟正文' } })
  fireEvent.click(screen.getByRole('button', { name: '确认并保存在本机' }))
  await waitFor(() => expect(onClose).toHaveBeenCalledOnce())
  expect(onError).toHaveBeenCalledWith('内容已保存；索引更新未完成，旧版本内容不会作为当前依据。', 'danger')
})
