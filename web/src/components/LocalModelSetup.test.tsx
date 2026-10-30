import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { LocalModelSetup } from './LocalModelSetup'
import type { Settings } from './settingsBadges'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

const ready: Settings['local_model'] = {
  model: 'BAAI/bge-small-zh-v1.5', revision: 'revision', dimensions: 512, token_limit: 512,
  download_size_bytes: 95_330_972, state: 'ready', downloaded_bytes: 95_330_972,
  progress_percent: 100, error_code: null,
}
const preparing: Settings['local_model'] = { ...ready, state: 'preparing', downloaded_bytes: 20, progress_percent: 1 }

it('offers a manual status retry after transient status reads fail', async () => {
  let failures = 0
  const fetchMock = vi.fn(async () => {
    if (failures < 3) { failures += 1; throw new Error('local status temporarily unavailable') }
    return Response.json(ready)
  })
  vi.stubGlobal('fetch', fetchMock)
  const onStatus = vi.fn()
  render(<LocalModelSetup status={preparing} onStatus={onStatus} />)

  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3), { timeout: 6000 })
  const retry = await screen.findByRole('button', { name: '重试读取准备状态' })
  expect(retry).toBeTruthy()
  fireEvent.click(retry)
  await waitFor(() => expect(onStatus).toHaveBeenCalledWith(ready))
}, 7_000)

it('ignores a late prepare response after the component unmounts', async () => {
  let resolveFetch: ((response: Response) => void) | undefined
  const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { resolveFetch = resolve }))
  vi.stubGlobal('fetch', fetchMock)
  const onStatus = vi.fn()
  const view = render(<LocalModelSetup status={{ ...ready, state: 'not_prepared' }} onStatus={onStatus} />)
  fireEvent.click(screen.getByRole('button', { name: '准备本地模型' }))
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1))
  view.unmount()

  await act(async () => { resolveFetch?.(Response.json(preparing)) })
  expect(onStatus).not.toHaveBeenCalled()
})
