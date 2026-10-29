import { describe, expect, it } from 'vitest'
import { buildFeishuAgentSetupPrompt } from './feishuAgentSetupPrompt'

describe('buildFeishuAgentSetupPrompt', () => {
  it('is portable across cwd and source availability while preserving safe setup gates', () => {
    const prompt = buildFeishuAgentSetupPrompt('http://localhost:5173/?token=secret#fragment')

    expect(prompt).toContain('请在本机为 SummitEverything')
    expect(prompt).toContain('当前工作目录')
    expect(prompt).toContain('知识工作库目录当作源码根目录')
    expect(prompt).toContain('只有确认源码目录确实属于上述运行实例后')
    expect(prompt).toContain('只有已验证源码根目录与运行实例匹配后')
    expect(prompt).toContain('docs/contracts/MCP-v1.md')
    expect(prompt).toContain('14 个受限工具')
    expect(prompt).toContain('一次性计划/授权')
    expect(prompt).toContain('不得代替用户确认或绕过计划')
    expect(prompt).toContain('API origin')
    expect(prompt).toContain('不能把网页端口擅自改猜成 8793')
    expect(prompt).toContain('若证据证实同源 API 或受支持的本机代理')
    expect(prompt).not.toContain('token=secret')
    expect(prompt).not.toContain('#fragment')
  })

  it('omits invalid origins and provides a safe fallback', () => {
    const prompt = buildFeishuAgentSetupPrompt('not a URL?token=secret')

    expect(prompt).toContain('当前 SummitEverything 页面')
    expect(prompt).not.toContain('not a URL')
    expect(prompt).not.toContain('token=secret')
  })
})
