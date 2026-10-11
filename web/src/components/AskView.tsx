import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { api, type Citation, type IndexPlan, type IndexResult } from '../api/client'
import type { components } from '../api/generated'

type Props = { onError: (message: string) => void; onOpenPage: (id: string, hash?: string) => void }
type IndexStatus = { fingerprint: string | null; pages: number; chunks: number; state: 'not_ready' | 'ready' | 'stale'; current_pages: number; stale_pages: number }
type StreamEvent = {
  request_id: string
  seq: number
  type: 'status' | 'citation' | 'delta' | 'completed' | 'error'
  data: Record<string, unknown>
}
type Settings = components['schemas']['SettingsSummary']
type Conversation = components['schemas']['ConversationDetail']
type Summary = Omit<Conversation, 'messages'>
type QueryState = 'idle' | 'running' | 'completed' | 'error' | 'cancelled' | 'interrupted'
type AnswerMode = 'fact' | 'comparison' | 'plan'
type AnswerRole = components['schemas']['AnswerRole']
type UserMemory = components['schemas']['UserMemory']
type MemoryCandidate = components['schemas']['MemoryCandidate']
const answerModeLabel: Record<AnswerMode, string> = {
  fact: '事实问答', comparison: '跨材料比较', plan: '工作方案',
}

const stateLabel: Record<QueryState, string> = {
  idle: '尚未提问',
  running: '正在回答',
  completed: '已完成',
  error: '回答失败',
  cancelled: '已取消',
  interrupted: '连接中断',
}

export function AskView({ onError, onOpenPage }: Props) {
  const [status, setStatus] = useState<IndexStatus | null>(null)
  const [plan, setPlan] = useState<IndexPlan | null>(null)
  const [result, setResult] = useState<IndexResult | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [citations, setCitations] = useState<Citation[]>([])
  const [streaming, setStreaming] = useState(false)
  const [requestId, setRequestId] = useState('')
  const [conversationId, setConversationId] = useState('')
  const [history, setHistory] = useState<Summary[]>([])
  const [historyCursor, setHistoryCursor] = useState<string | null>(null)
  const [thread, setThread] = useState<Conversation | null>(null)
  const [queryState, setQueryState] = useState<QueryState>('idle')
  const [notice, setNotice] = useState('')
  const [answerMode, setAnswerMode] = useState<AnswerMode>('fact')
  const [roles, setRoles] = useState<AnswerRole[]>([])
  const [selectedRoleId, setSelectedRoleId] = useState('')
  const [roleName, setRoleName] = useState('')
  const [roleInstructions, setRoleInstructions] = useState('')
  const [roleBudget, setRoleBudget] = useState(2000)
  const [memories, setMemories] = useState<UserMemory[]>([])
  const [memoryCandidates, setMemoryCandidates] = useState<MemoryCandidate[]>([])
  const [memoryDrafts, setMemoryDrafts] = useState<Record<string, string>>({})
  const [candidateDrafts, setCandidateDrafts] = useState<Record<string, string>>({})
  const [memoryAttestations, setMemoryAttestations] = useState<Record<string, boolean>>({})
  const [answerDetails, setAnswerDetails] = useState<Pick<components['schemas']['Answer'], 'source_statements' | 'inferences' | 'advice' | 'missing_information'> | null>(null)
  const abortController = useRef<AbortController | null>(null)
  const historyCursorRef = useRef<string | null>(null)
  const confirmationIds = useRef<Record<string, string>>({})

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await api.get<IndexStatus>('/index/status'))
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法读取索引状态')
    }
  }, [onError])

  const refreshHistory = useCallback(async (append = false) => {
    try {
      const cursor = append ? historyCursorRef.current : null
      const query = new URLSearchParams({ limit: '20' })
      if (cursor) query.set('cursor', cursor)
      const page = await api.get<{ items: Summary[]; next_cursor: string | null }>(`/conversations?${query}`)
      setHistory((current) => append ? [...current, ...page.items] : page.items)
      historyCursorRef.current = page.next_cursor
      setHistoryCursor(page.next_cursor)
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法读取问答历史')
    }
  }, [onError])

  const refreshPersonalization = useCallback(async () => {
    try {
      const [roleItems, memoryItems, candidateItems] = await Promise.all([
        api.get<AnswerRole[]>('/roles'), api.get<UserMemory[]>('/memory'),
        api.get<MemoryCandidate[]>('/memory/candidates'),
      ])
      setRoles(roleItems)
      setMemories(memoryItems)
      setMemoryCandidates(candidateItems)
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法读取本机问答偏好')
    }
  }, [onError])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshStatus()
      void refreshHistory()
      void refreshPersonalization()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [refreshHistory, refreshPersonalization, refreshStatus])

  async function createPlan() {
    setResult(null)
    try {
      const settings = await api.get<Settings>('/settings')
      const fingerprint = settings.embedding_fingerprint
      const mode = !status?.fingerprint ? 'initial' : status.fingerprint === fingerprint ? 'incremental' : 'model_change'
      const next = await api.post<IndexPlan>('/index/plans', { mode, fingerprint })
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

  async function openConversation(id: string) {
    try {
      const next = await api.post<Conversation>(`/conversations/${id}/reopen`, {})
      setThread(next)
      setConversationId(next.conversation_id)
      setQueryState(next.state)
      const latest = next.messages.at(-1)
      setAnswer(latest?.answer ?? '')
      setCitations(latest?.citations ?? [])
      setAnswerDetails(latest ? {
        source_statements: latest.source_statements ?? [],
        inferences: latest.inferences ?? [], advice: latest.advice ?? [],
        missing_information: latest.missing_information ?? [],
      } : null)
      if (latest?.answer_mode) setAnswerMode(latest.answer_mode)
      setNotice(latest?.state === 'interrupted'
        ? '上次连接中断；已保存实际收到的部分内容。不会自动重新发送，请自行决定是否继续提问。'
        : '')
      setRequestId(latest?.request_id ?? '')
      setQuestion('')
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法打开问答历史')
    }
  }

  function startNewConversation() {
    setThread(null)
    setConversationId('')
    setRequestId('')
    setQuestion('')
    setAnswer('')
    setCitations([])
    setAnswerDetails(null)
    setQueryState('idle')
    setNotice('')
    setAnswerDetails(null)
  }

  async function saveRole() {
    const payload = { name: roleName.trim(), instructions: roleInstructions.trim(), context_budget: roleBudget }
    try {
      const role = selectedRoleId
        ? await api.patch<AnswerRole>(`/roles/${selectedRoleId}`, payload)
        : await api.post<AnswerRole>('/roles', payload)
      setSelectedRoleId(role.role_id)
      setRoleName(role.name)
      setRoleInstructions(role.instructions)
      setRoleBudget(role.context_budget)
      await refreshPersonalization()
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '角色没有保存')
    }
  }

  function chooseRole(roleId: string) {
    setSelectedRoleId(roleId)
    const role = roles.find((item) => item.role_id === roleId)
    setRoleName(role?.name ?? '')
    setRoleInstructions(role?.instructions ?? '')
    setRoleBudget(role?.context_budget ?? 2000)
  }

  async function deleteRole() {
    if (!selectedRoleId) return
    try {
      await api.delete(`/roles/${selectedRoleId}`)
      chooseRole('')
      await refreshPersonalization()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '角色没有删除')
    }
  }

  async function proposeMemory(message: Conversation['messages'][number]) {
    if (!memoryAttestations[message.request_id]) return
    try {
      await api.post('/memory/candidates', {
        message_id: message.request_id, text: message.question, user_expression: true,
      })
      await refreshPersonalization()
      setMemoryAttestations((current) => ({ ...current, [message.request_id]: false }))
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '这句内容不能作为记忆候选')
    }
  }

  async function confirmMemory(candidate: MemoryCandidate) {
    try {
      const confirmationId = confirmationIds.current[candidate.candidate_id]
        ?? (confirmationIds.current[candidate.candidate_id] = crypto.randomUUID())
      await api.post(`/memory/candidates/${candidate.candidate_id}/confirmations`, {
        confirmation_id: confirmationId, text: candidateDrafts[candidate.candidate_id] ?? candidate.text,
      })
      await refreshPersonalization()
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '记忆没有确认')
    }
  }

  async function deleteConversation(id: string) {
    try {
      await api.delete(`/conversations/${id}`)
      setHistory((current) => current.filter((item) => item.conversation_id !== id))
      if (conversationId === id) startNewConversation()
      await refreshHistory()
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法删除问答历史')
    }
  }

  async function ask(event: FormEvent) {
    event.preventDefault()
    if (!question.trim() || streaming) return
    const controller = new AbortController()
    const queryId = crypto.randomUUID()
    let targetConversation = conversationId
    abortController.current = controller
    setStreaming(true)
    setQueryState('running')
    setAnswer('')
    setCitations([])
    setAnswerDetails(null)
    setRequestId(queryId)
    if (targetConversation) setConversationId(targetConversation)
    setNotice('')
    onError('')
    try {
      const settings = await api.get<Settings>('/settings')
      const response = await fetch('/api/v1/queries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          ...(targetConversation ? { conversation_id: targetConversation } : {}),
          fingerprint: settings.embedding_fingerprint,
          purpose: 'current',
          answer_mode: answerMode,
          ...(selectedRoleId ? { role_id: selectedRoleId } : {}),
          request_id: queryId,
        }),
        signal: controller.signal,
      })
      if (!response.ok) {
        const failure = await response.json().catch(() => null) as { error?: { message?: string } } | null
        throw new Error(failure?.error?.message ?? '知识问答暂不可用。')
      }
      if (!response.body) throw new Error('问答服务没有返回内容；请从本机历史确认保存状态后再继续。')
      const responseConversation = response.headers.get('X-Conversation-ID')
      if (responseConversation) {
        if (targetConversation && responseConversation !== targetConversation) {
          throw new Error('问答流返回了不匹配的会话；已保留本机历史。')
        }
        targetConversation = responseConversation
        setConversationId(responseConversation)
      } else if (!targetConversation) {
        throw new Error('问答服务未返回会话编号；请从本机历史确认保存状态后再继续。')
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''
      let lastSeq = 0
      let sawTerminal = false
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
            if (message.request_id !== queryId || message.seq !== lastSeq + 1 || sawTerminal) {
              throw new Error('问答流顺序异常；已保留本机历史，不会自动重发。')
            }
            lastSeq = message.seq
            if (message.type === 'citation') {
              setCitations((current) => [...current, message.data as unknown as Citation])
            } else if (message.type === 'delta') {
              accumulated += String(message.data.text ?? '')
              setAnswer(accumulated)
            } else if (message.type === 'completed') {
              sawTerminal = true
              accumulated = String(message.data.text ?? accumulated)
              setAnswer(accumulated)
              setAnswerDetails({
                source_statements: (message.data.source_statements as string[] | undefined) ?? [],
                inferences: (message.data.inferences as string[] | undefined) ?? [],
                advice: (message.data.advice as string[] | undefined) ?? [],
                missing_information: (message.data.missing_information as string[] | undefined) ?? [],
              })
              setQueryState('completed')
            } else if (message.type === 'error') {
              sawTerminal = true
              const cancelled = message.data.code === 'cancelled'
              setQueryState(cancelled ? 'cancelled' : 'error')
              setNotice(String(message.data.message ?? '问答未能完成。'))
            }
          }
          boundary = buffer.indexOf('\n\n')
        }
      }
      if (!sawTerminal) {
        setQueryState('interrupted')
        setNotice('连接已结束，回答未完整送达。已保留实际收到的部分；不会自动重新发送。可从历史继续提问。')
      }
      if (targetConversation) setThread(await api.post<Conversation>(`/conversations/${targetConversation}/reopen`, {}))
      await refreshHistory()
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'AbortError') {
        setQueryState('cancelled')
        setNotice('已请求取消。已收到的部分会留在本机历史中，不会自动重发。')
      } else {
        setQueryState('interrupted')
        setNotice(cause instanceof Error ? cause.message : '知识问答连接中断')
      }
      await refreshHistory()
      const existing = targetConversation
        ? await api.post<Conversation>(`/conversations/${targetConversation}/reopen`, {}).catch(() => null)
        : null
      if (existing) setThread(existing)
    } finally {
      setStreaming(false)
      abortController.current = null
    }
  }

  async function cancel() {
    if (requestId) await api.delete('/queries/' + requestId).catch(() => undefined)
    abortController.current?.abort()
  }

  function openCitation(citation: Citation) {
    if (citation.availability === 'unavailable') {
      setNotice('这条引用对应的页面已删除、待确认或不再具备问答资格，无法作为当前依据打开。')
      return
    }
    if (citation.availability === 'updated') {
      onOpenPage(citation.page_id, citation.content_sha256)
      return
    }
    setNotice('')
    onOpenPage(citation.page_id, citation.content_sha256)
  }

  const renderedMessages = thread?.messages ?? []

  return (
    <section className="content-wrap ask-view">
      <div className="page-heading">
        <div><div className="eyebrow">仅使用已确认知识</div><h1>知识问答</h1><p className="lede">每条依据都会回到回答当时的页面版本复核。没有资料时会明确说明。</p></div>
        <button className="button secondary" onClick={startNewConversation}>新建对话</button>
      </div>
      <section className="conversation-history" aria-label="本机问答历史">
        <div className="section-title-row"><h2>本机历史</h2><span>只保存在此 profile 和工作库</span></div>
        {history.length === 0 ? <p className="empty-state">还没有问答历史。</p> : <ul>
          {history.map((item) => <li key={item.conversation_id} className={item.conversation_id === conversationId ? 'selected' : ''}>
            <button className="history-open" onClick={() => void openConversation(item.conversation_id)}>
              <strong>{item.title}</strong><small>{new Date(item.updated_at).toLocaleString()} · {item.message_count} 个问题 · {stateLabel[item.state]}</small>
            </button>
            <button className="text-button" aria-label={`删除 ${item.title}`} onClick={() => void deleteConversation(item.conversation_id)}>删除</button>
          </li>)}
        </ul>}
        {historyCursor && <button className="text-button" onClick={() => void refreshHistory(true)}>加载更早历史</button>}
      </section>
      <section className="index-status-panel">
        <div className="index-status-copy">
          <span className={status?.state === 'ready' ? 'index-state ready' : 'index-state'}>{status?.state === 'stale' ? '本机索引有待更新' : status?.fingerprint ? '本机索引已就绪' : '还没有本机索引'}</span>
          <p>{status?.state === 'stale' ? `${status.stale_pages} 个页面版本尚未进入索引；旧版本不会作为当前依据。可确认增量计划更新。` : status?.fingerprint ? status.pages + ' 个页面 · ' + status.chunks + ' 个分块 · ' + status.fingerprint : '创建计划会展示本次范围与估算，再由你确认运行。'}</p>
        </div>
        <div className="index-actions">{!plan ? <button className="button secondary" onClick={createPlan}>准备索引计划</button> : <button className="button primary" onClick={executePlan}>按计划创建索引</button>}</div>
      </section>
      {plan && <section className="plan-card" aria-live="polite"><div><strong>索引计划待确认</strong><span>{plan.mode === 'initial' ? '首次构建' : '增量更新'} · {plan.page_ids.length} 个页面</span></div><p>约 {plan.estimated_tokens.toLocaleString()} 个文本 token；{plan.estimated_cost === null ? '当前无法估算 provider 费用，请先在控制台确认预算。' : '本机 Fake embedding 费用为 ¥0。'}</p><button className="text-button" onClick={() => setPlan(null)}>取消计划</button></section>}
      {result && <p role="status" className="success-note">已保存到本机：{result.indexed_pages} 页，{result.embedded_chunks} 个新分块，复用 {result.reused_chunks} 个。</p>}

      <section className="conversation-history" aria-label="本机问答偏好与记忆">
        <div className="section-title-row"><h2>问答角色与记忆</h2><span>只调整表达与指代理解，不改变证据或权限</span></div>
        <label htmlFor="answer-role">使用角色</label>
        <select id="answer-role" value={selectedRoleId} onChange={(event) => chooseRole(event.target.value)}>
          <option value="">不使用角色</option>{roles.map((role) => <option key={role.role_id} value={role.role_id}>{role.name}</option>)}
        </select>
        <label htmlFor="role-name">角色名称</label>
        <input id="role-name" value={roleName} maxLength={80} onChange={(event) => setRoleName(event.target.value)} placeholder="例如：简明分析" />
        <label htmlFor="role-guidance">表达偏好</label>
        <textarea id="role-guidance" value={roleInstructions} maxLength={4000} onChange={(event) => setRoleInstructions(event.target.value)} placeholder="只调整表达方式；不能改变证据标准或执行权限。" rows={2} />
        <label htmlFor="role-budget">角色说明预算（字节）</label>
        <input id="role-budget" type="number" min={0} max={6000} value={roleBudget} onChange={(event) => setRoleBudget(Number(event.target.value))} />
        <div className="button-row"><button className="button secondary" onClick={() => void saveRole()} disabled={!roleName.trim()}>保存角色</button>{selectedRoleId && <button className="text-button" onClick={() => void deleteRole()}>删除角色</button>}</div>
        <h3>待确认记忆</h3>
        {memoryCandidates.length === 0 ? <p className="empty-state">没有待确认记忆。</p> : memoryCandidates.map((candidate) => <div key={candidate.candidate_id} className="memory-item">
          <textarea aria-label="编辑记忆候选" value={candidateDrafts[candidate.candidate_id] ?? candidate.text} onChange={(event) => setCandidateDrafts((current) => ({ ...current, [candidate.candidate_id]: event.target.value }))} />
          <small>来自本机历史中的本人问题；确认后才会用于回答。</small>
          <button className="button secondary" onClick={() => void confirmMemory(candidate)}>确认并保存</button>
        </div>)}
        <h3>已确认记忆</h3>
        {memories.length === 0 ? <p className="empty-state">目前没有已确认记忆。</p> : memories.map((memory) => <div key={memory.memory_id} className="memory-item">
          <textarea aria-label="编辑已确认记忆" value={memoryDrafts[memory.memory_id] ?? memory.text} onChange={(event) => setMemoryDrafts((current) => ({ ...current, [memory.memory_id]: event.target.value }))} />
          <small>来源问题：{memory.source_message_id}</small>
          <div className="button-row"><button className="text-button" onClick={() => void api.patch(`/memory/${memory.memory_id}`, { text: memoryDrafts[memory.memory_id] ?? memory.text }).then(refreshPersonalization).catch((cause: unknown) => onError(cause instanceof Error ? cause.message : '记忆没有保存修改'))}>保存修改</button><button className="text-button" onClick={() => void api.delete(`/memory/${memory.memory_id}`).then(refreshPersonalization).catch((cause: unknown) => onError(cause instanceof Error ? cause.message : '记忆没有删除'))}>删除记忆</button></div>
        </div>)}
      </section>

      {renderedMessages.length > 0 && <section className="conversation-thread" aria-label="对话内容">
        <h2>{thread?.title}</h2>
        {renderedMessages.map((message) => <article className="conversation-turn" key={message.request_id}>
          <div className="user-question"><strong>你</strong><p>{message.question}</p></div>
          <div className="assistant-answer"><strong>回答 · {answerModeLabel[message.answer_mode]} · {stateLabel[message.state]}</strong><pre className="answer-text">{message.answer || (message.state === 'running' ? '正在检索与整理…' : '尚无回答内容')}</pre>
            <AnswerDetails details={message} />
            <label className="memory-attestation"><input type="checkbox" checked={memoryAttestations[message.request_id] ?? false} onChange={(event) => setMemoryAttestations((current) => ({ ...current, [message.request_id]: event.target.checked }))} />这是我本人表达的偏好或事实，不是我粘贴、转述的材料或引用</label>
            <button className="text-button" disabled={!memoryAttestations[message.request_id]} onClick={() => void proposeMemory(message)}>创建待确认记忆候选</button>
            {message.error && <p role="status" className="form-error">{message.error}</p>}
            {(message.citations?.length ?? 0) > 0 && <CitationList citations={message.citations ?? []} onOpen={openCitation} />}
          </div>
        </article>)}
      </section>}

      <form className="query-form" onSubmit={ask}>
        <label htmlFor="answer-mode">回答方式</label>
        <select id="answer-mode" value={answerMode} onChange={(event) => setAnswerMode(event.target.value as AnswerMode)}>
          <option value="fact">查找事实</option><option value="comparison">跨材料比较</option><option value="plan">提出工作方案</option>
        </select>
        <label htmlFor="query-role">本次使用角色</label>
        <select id="query-role" value={selectedRoleId} onChange={(event) => chooseRole(event.target.value)}>
          <option value="">不使用角色</option>{roles.map((role) => <option key={role.role_id} value={role.role_id}>{role.name}</option>)}
        </select>
        <label htmlFor="knowledge-question">你的问题</label>
        <div className="query-input-wrap">
          <textarea id="knowledge-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：这个项目已经确认的地点和联系人有哪些？" rows={3} />
          {streaming ? <button type="button" className="button secondary" onClick={cancel}>停止回答</button> : <button className="button primary" disabled={!question.trim()}>开始检索</button>}
        </div>
        <small>回答与历史仅保存在本机；不会自动写入知识页。</small>
      </form>

      {(answer || citations.length > 0 || queryState !== 'idle') && (!thread?.messages.some((message) => message.request_id === requestId) || streaming) && <section className="answer-panel" aria-live="polite">
        <div className="answer-heading"><span className="answer-mark">答</span><div><h2>本次回答 · {stateLabel[queryState]}</h2><span>{streaming ? '正在读取当前页面…' : citations.length ? '根据已确认资料' : '没有找到可引用的依据'}</span></div></div>
        <pre className="answer-text">{answer}</pre>
        {answerDetails && <AnswerDetails details={answerDetails} />}
        {notice && <p role="status" className={queryState === 'error' ? 'form-error' : 'stale-citation-note'}>{notice}</p>}
        {citations.length > 0 && <CitationList citations={citations} onOpen={openCitation} />}
      </section>}
    </section>
  )
}

function AnswerDetails({ details }: { details: Partial<Pick<components['schemas']['Answer'], 'source_statements' | 'inferences' | 'advice' | 'missing_information'>> }) {
  const sections = [
    ['已确认资料中的陈述', details.source_statements],
    ['推断', details.inferences], ['建议', details.advice], ['尚缺资料', details.missing_information],
  ] as const
  return <div className="answer-details">
    {sections.filter(([, items]) => (items?.length ?? 0) > 0).map(([label, items]) => <div key={label}><strong>{label}</strong><ul>{items?.map((item, index) => <li key={`${label}-${index}`}>{item}</li>)}</ul></div>)}
  </div>
}

function CitationList({ citations, onOpen }: { citations: Citation[]; onOpen: (citation: Citation) => void }) {
  return <div className="citation-list">
    <h3>引用依据</h3>
    {citations.map((citation, index) => <button key={`${citation.page_id}:${citation.content_sha256}:${index}`} className="citation-card" onClick={() => onOpen(citation)}>
      <span className="citation-number">{index + 1}</span>
      <span><strong>{citation.heading || '页面内容'}</strong><small>{citation.excerpt}</small><small>{citation.availability === 'updated' ? '原引用版本已更新' : citation.availability === 'unavailable' ? '原引用已不可用' : citation.validity === 'superseded' ? '历史版本，仅限历史参考' : '引用版本仍可用'}</small></span>
      <span aria-hidden="true">↗</span>
    </button>)}
  </div>
}
