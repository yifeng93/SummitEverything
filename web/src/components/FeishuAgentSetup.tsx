import { useState } from 'react'
import { buildFeishuAgentSetupPrompt } from './feishuAgentSetupPrompt'
import './FeishuAgentSetup.css'

export function FeishuAgentSetup({ className = 'button secondary' }: { className?: string }) {
  const [failed, setFailed] = useState(false)
  const [copied, setCopied] = useState(false)
  const [copying, setCopying] = useState(false)
  const prompt = buildFeishuAgentSetupPrompt(window.location.origin)

  async function copyPrompt() {
    if (copying) return
    setCopying(true)
    setCopied(false)
    try {
      if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable')
      await navigator.clipboard.writeText(prompt)
      setFailed(false)
      setCopied(true)
    } catch {
      setFailed(true)
    } finally {
      setCopying(false)
    }
  }

  return <div className="feishu-agent-setup">
    <button className={className} type="button" disabled={copying} onClick={() => void copyPrompt()}>{copying ? '正在复制…' : '连接飞书'}</button>
    {copied && <p className="feishu-agent-setup-feedback" role="status">已复制，粘贴到 Codex / WorkBuddy 开始自动配置。</p>}
    {failed && <div className="feishu-agent-setup-fallback">
      <p className="form-error" role="alert">无法自动复制。选择下面的只读提示词，再粘贴到 Codex / WorkBuddy；也可以重试。</p>
      <textarea aria-label="飞书接入提示词" readOnly value={prompt} onFocus={(event) => event.currentTarget.select()} />
      <button className="button secondary" type="button" onClick={() => void copyPrompt()}>重试复制</button>
    </div>}
  </div>
}
