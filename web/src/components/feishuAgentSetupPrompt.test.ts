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
    expect(prompt).toContain('日历是只读例外')
    expect(prompt).toContain('材料/任务读取与材料导入须先核实现有一次性计划')
    expect(prompt).toContain('不得代替用户确认或绕过计划')
    expect(prompt).toContain('先核实它要求的身份、scope 及目标资源归属')
    expect(prompt).toContain('机器人/应用的主日历不等同于用户个人日历')
    expect(prompt).toContain('只对确需的 user scope 请求用户授权')
    expect(prompt).toContain('若缺的是 app scope，则报告需管理员开通/审批的具体权限')
    expect(prompt).toContain('外部结果为 unknown 时先查看可用回执/状态，不自动重试')
    expect(prompt).toContain('返回 0 条或成功读取机器人主日历')
    expect(prompt).toContain('不能证明用户个人日历正确')
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
