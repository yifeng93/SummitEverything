import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import { FeishuAgentSetup } from './FeishuAgentSetup'

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('copies a self-contained prompt using only the sanitized current origin', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined)
  vi.stubGlobal('location', { origin: 'http://localhost:5173', href: 'http://localhost:5173/?token=secret#secret' })
  vi.stubGlobal('navigator', { clipboard: { writeText } })
  render(<FeishuAgentSetup />)
  fireEvent.click(screen.getByRole('button', { name: '连接飞书' }))
  expect((await screen.findByRole('status')).textContent).toContain('已复制')
  expect(writeText).toHaveBeenCalledTimes(1)
  expect(writeText.mock.calls[0][0]).toContain('http://localhost:5173')
  expect(writeText.mock.calls[0][0]).not.toContain('secret')
  expect(writeText.mock.calls[0][0]).toContain('docs/contracts/MCP-v1.md')
  expect(writeText.mock.calls[0][0]).toContain('PUT /credentials/{provider}')
  expect(screen.queryByRole('textbox')).toBeNull()
})

it('offers selectable prompt text and retries when clipboard access is rejected', async () => {
  const writeText = vi.fn().mockRejectedValueOnce(new Error('denied')).mockResolvedValueOnce(undefined)
  vi.stubGlobal('navigator', { clipboard: { writeText } })
  render(<FeishuAgentSetup />)
  fireEvent.click(screen.getByRole('button', { name: '连接飞书' }))
  const prompt = await screen.findByRole('textbox', { name: '飞书接入提示词' })
  expect((prompt as HTMLTextAreaElement).value).toContain('请在本机')
  fireEvent.click(screen.getByRole('button', { name: '重试复制' }))
  expect(await screen.findByRole('button', { name: /已复制/ })).toBeTruthy()
  expect(writeText).toHaveBeenCalledTimes(2)
  expect(screen.queryByRole('textbox')).toBeNull()
})
