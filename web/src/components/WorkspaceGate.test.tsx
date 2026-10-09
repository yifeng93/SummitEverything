import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { WorkspaceGate } from './WorkspaceGate'

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

it('creates a workspace through the local API and forwards the returned context', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'stable-operation-id' })
  const workspace = {
    workspace_id: 'workspace-id',
    root: '/tmp/synthetic',
    local_profile_dir: '/tmp/profile',
    name: '模拟工作库',
    read_only: false,
  }
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    status: 201,
    json: async () => workspace,
  })
  vi.stubGlobal('fetch', fetchMock)
  const onOpened = vi.fn()
  render(<WorkspaceGate onOpened={onOpened} />)

  fireEvent.change(screen.getByLabelText('工作库名称'), { target: { value: '模拟工作库' } })
  fireEvent.change(screen.getByLabelText('文件夹路径'), { target: { value: '/tmp/synthetic' } })
  fireEvent.click(screen.getByRole('button', { name: '创建本地工作库' }))

  await waitFor(() => expect(onOpened).toHaveBeenCalledWith(workspace))
  const [url, options] = fetchMock.mock.calls[0] as [string, RequestInit]
  expect(url).toBe('/api/v1/workspaces')
  expect(JSON.parse(String(options.body))).toEqual({
    root: '/tmp/synthetic',
    mode: 'create',
    name: '模拟工作库',
    operation_id: 'stable-operation-id',
  })
})

it('keeps the setup form visible and explains a rejected workspace', async () => {
  vi.stubGlobal('crypto', { randomUUID: () => 'operation-id' })
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: false,
    status: 409,
    json: async () => ({ error: { message: '所选目录不是空目录' } }),
  }))
  render(<WorkspaceGate onOpened={vi.fn()} />)
  fireEvent.change(screen.getByLabelText('工作库名称'), { target: { value: '模拟工作库' } })
  fireEvent.change(screen.getByLabelText('文件夹路径'), { target: { value: '/tmp/existing' } })
  fireEvent.click(screen.getByRole('button', { name: '创建本地工作库' }))
  expect((await screen.findByRole('alert')).textContent).toContain('所选目录不是空目录')
})
