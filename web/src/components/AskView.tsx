import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Citation, type IndexPlan, type IndexResult } from '../api/client'

type Props = { onError: (message: string) => void; onOpenPage: (id: string, hash?: string) => void }
type IndexStatus = { fingerprint: string | null; pages: number; chunks: number; state: 'not_ready' | 'ready' | 'stale'; current_pages: number; stale_pages: number }
type StreamEvent = {
  request_id: string
  seq: number
  type: 'status' | 'citation' | 'delta' | 'completed' | 'error'
  data: Record<string, unknown>
}
const fingerprint = 'summit-fake-embedding-v1'

export function AskView({ onError, onOpenPage }: Props) {
  const [status, setStatus] = useState<IndexStatus | null>(null)
  const [plan, setPlan] = useState<IndexPlan | null>(null)
  const [result, setResult] = useState<IndexResult | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [citations, setCitations] = useState<Citation[]>([])
  const [streaming, setStreaming] = useState(false)
  const [requestId, setRequestId] = useState('')
  const abortController = useRef<AbortController | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await api.get<IndexStatus>('/index/status'))
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法读取索引状态')
    }
  }, [onError])

  useEffect(() => { void refreshStatus() }, [refreshStatus])

  async function createPlan() {
    setResult(null)
    try {
      const next = await api.post<IndexPlan>('/index/plans', {
        mode: status?.fingerprint ? 'incremental' : 'initial',
        fingerprint,
      })
      setPlan(next)
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法生成索引计划')
    }
  }

  async function executePlan() {
    if (!plan) return
    try {
      const next = await api.post<IndexResult>('/index/jobs', plan)
      setResult(next)
      setPlan(null)
      await refreshStatus()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '索引没有完成')
    }
  }

  async function ask(event: FormEvent) {
    event.preventDefault()
    if (!question.trim()) return
    const controller = new AbortController()
    const queryId = crypto.randomUUID()
    abortController.current = controller
    setStreaming(true)
    setAnswer('')
    setCitations([])
    setRequestId(queryId)
    onError('')
    try {
      const response = await fetch('/api/v1/queries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, fingerprint, purpose: 'current', request_id: queryId }),
        signal: controller.signal,
      })
      if (!response.ok || !response.body) throw new Error('知识问答暂不可用。')
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let boundary = buffer.indexOf('\n\n')
        while (boundary >= 0) {
          const block = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          const dataLine = block.split('\n').find((line) => line.startsWith('data: '))
          if (dataLine) {
            const message = JSON.parse(dataLine.slice(6)) as StreamEvent
            setRequestId(message.request_id)
            if (message.type === 'citation') {
              setCitations((current) => [...current, message.data as unknown as Citation])
            } else if (message.type === 'delta') {
              accumulated += String(message.data.text ?? '')
              setAnswer(accumulated)
            } else if (message.type === 'completed') {
              setAnswer(String(message.data.text ?? accumulated))
            } else if (message.type === 'error') {
              throw new Error(String(message.data.message ?? '查询已停止'))
            }
          }
          boundary = buffer.indexOf('\n\n')
        }
      }
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'AbortError') {
        onError('查询已取消，尚未生成完整回答。')
      } else {
        onError(cause instanceof Error ? cause.message : '知识问答失败')
      }
    } finally {
      setStreaming(false)
      abortController.current = null
    }
  }

  async function cancel() {
    if (requestId) await api.delete('/queries/' + requestId).catch(() => undefined)
    abortController.current?.abort()
  }

  return (
    <section className="content-wrap ask-view">
      <div className="page-heading">
        <div><div className="eyebrow">仅使用已确认知识</div><h1>知识问答</h1><p className="lede">每条依据都会回到当前页面版本复核。没有资料时会明确说明。</p></div>
      </div>
      <section className="index-status-panel">
        <div className="index-status-copy">
          <span className={status?.state === 'ready' ? 'index-state ready' : 'index-state'}>{status?.state === 'stale' ? '本机索引有待更新' : status?.fingerprint ? '本机索引已就绪' : '还没有本机索引'}</span>
          <p>{status?.state === 'stale' ? `${status.stale_pages} 个页面版本尚未进入索引；旧版本不会作为当前依据。可确认增量计划更新。` : status?.fingerprint ? status.pages + ' 个页面 · ' + status.chunks + ' 个分块 · ' + status.fingerprint : '创建计划会展示本次范围与估算，再由你确认运行。'}</p>
        </div>
        <div className="index-actions">
          {!plan ? <button className="button secondary" onClick={createPlan}>准备索引计划</button> : (
            <button className="button primary" onClick={executePlan}>按计划创建索引</button>
          )}
        </div>
      </section>
      {plan && (
        <section className="plan-card" aria-live="polite">
          <div><strong>索引计划待确认</strong><span>{plan.mode === 'initial' ? '首次构建' : '增量更新'} · {plan.page_ids.length} 个页面</span></div>
          <p>约 {plan.estimated_tokens.toLocaleString()} 个文本 token；本地 Fake embedding 费用为 ¥0。</p>
          <button className="text-button" onClick={() => setPlan(null)}>取消计划</button>
        </section>
      )}
      {result && <p role="status" className="success-note">已保存到本机：{result.indexed_pages} 页，{result.embedded_chunks} 个新分块，复用 {result.reused_chunks} 个。</p>}

      <form className="query-form" onSubmit={ask}>
        <label htmlFor="knowledge-question">你的问题</label>
        <div className="query-input-wrap">
          <textarea id="knowledge-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：这个项目已经确认的地点和联系人有哪些？" rows={3} />
          {streaming ? <button type="button" className="button secondary" onClick={cancel}>停止回答</button> : <button className="button primary" disabled={!question.trim()}>开始检索</button>}
        </div>
        <small>答案使用本地模拟检索，不会访问云端模型。</small>
      </form>

      {(answer || citations.length > 0) && (
        <section className="answer-panel" aria-live="polite">
          <div className="answer-heading"><span className="answer-mark">答</span><div><h2>检索结果</h2><span>{streaming ? '正在读取当前页面…' : citations.length ? '根据已确认资料' : '没有找到可引用的依据'}</span></div></div>
          <pre className="answer-text">{answer}</pre>
          {citations.length > 0 && <div className="citation-list">
            <h3>引用依据</h3>
            {citations.map((citation, index) => (
              <button key={citation.chunk_id} className="citation-card" onClick={() => onOpenPage(citation.page_id, citation.content_sha256)}>
                <span className="citation-number">{index + 1}</span>
                <span><strong>{citation.heading || '页面内容'}</strong><small>{citation.excerpt}</small></span>
                <span aria-hidden="true">↗</span>
              </button>
            ))}
          </div>}
        </section>
      )}
    </section>
  )
}
