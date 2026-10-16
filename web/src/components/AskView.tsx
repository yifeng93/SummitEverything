import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { api, sessionHeaders, type Citation, type Page } from '../api/client'
import type { components } from '../api/generated'
import { ConfirmDialog } from './ConfirmDialog'
import { StreamingMarkdown } from './StreamingMarkdown'

type Props = { onError: (message: string) => void; onOpenPage: (id: string, hash?: string) => void; onOpenApproval?: () => void }
type IndexStatus = { fingerprint: string | null; pages: number; chunks: number; state: 'not_ready' | 'ready' | 'stale'; current_pages: number; stale_pages: number }
type StreamEvent = {
  request_id: string
  seq: number
  type: 'status' | 'citation' | 'delta' | 'completed' | 'error'
  data: Record<string, unknown>
}
type Settings = components['schemas']['SettingsSummary']
type AcceptancePlan = { plan_id: string; scope_sha256: string; request_limit: number }
type PendingQuery = { plan: AcceptancePlan; scope: Record<string, unknown>; body: Record<string, unknown> }
type Conversation = components['schemas']['ConversationDetail']
type Summary = Omit<Conversation, 'messages'>
type QueryState = 'idle' | 'running' | 'completed' | 'error' | 'cancelled' | 'interrupted'
type AnswerMode = 'fact' | 'comparison' | 'plan'
type RetrievalPurpose = 'current' | 'history'
type AnswerRole = components['schemas']['AnswerRole']
type UserMemory = components['schemas']['UserMemory']
type MemoryCandidate = components['schemas']['MemoryCandidate']
type PendingDelete = { kind: 'conversation' | 'role' | 'memory'; id: string; label: string }
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

export function AskView({ onError, onOpenPage, onOpenApproval }: Props) {
  const [status, setStatus] = useState<IndexStatus | null>(null)
  const [eligiblePages, setEligiblePages] = useState<Page[]>([])
  const [pendingQuery, setPendingQuery] = useState<PendingQuery | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [citations, setCitations] = useState<Citation[]>([])
  const [streaming, setStreaming] = useState(false)
  const [requestId, setRequestId] = useState('')
  const [conversationId, setConversationId] = useState('')
  const [history, setHistory] = useState<Summary[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState('')
  const [historyCursor, setHistoryCursor] = useState<string | null>(null)
  const [thread, setThread] = useState<Conversation | null>(null)
  const [queryState, setQueryState] = useState<QueryState>('idle')
  const [notice, setNotice] = useState('')
  const [answerMode, setAnswerMode] = useState<AnswerMode>('fact')
  const [retrievalPurpose, setRetrievalPurpose] = useState<RetrievalPurpose>('current')
  const [roles, setRoles] = useState<AnswerRole[]>([])
  const [selectedRoleId, setSelectedRoleId] = useState('')
  const [roleName, setRoleName] = useState('')
  const [roleInstructions, setRoleInstructions] = useState('')
  const [roleBudget, setRoleBudget] = useState(2000)
  const [memories, setMemories] = useState<UserMemory[]>([])
  const [memoryCandidates, setMemoryCandidates] = useState<MemoryCandidate[]>([])
  const [personalizationLoading, setPersonalizationLoading] = useState(true)
  const [personalizationError, setPersonalizationError] = useState('')
  const [memoryDrafts, setMemoryDrafts] = useState<Record<string, string>>({})
  const [candidateDrafts, setCandidateDrafts] = useState<Record<string, string>>({})
  const [memoryAttestations, setMemoryAttestations] = useState<Record<string, boolean>>({})
  const [answerDetails, setAnswerDetails] = useState<Pick<components['schemas']['Answer'], 'source_statements' | 'inferences' | 'advice' | 'missing_information'> | null>(null)
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null)
  const abortController = useRef<AbortController | null>(null)
  const historyCursorRef = useRef<string | null>(null)
  const confirmationIds = useRef<Record<string, string>>({})
  const approvedQuery = useRef<{ planId: string; body: Record<string, unknown> } | null>(null)
  const queryForm = useRef<HTMLFormElement | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await api.get<IndexStatus>('/index/status'))
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法读取索引状态')
    }
  }, [onError])

  const refreshHistory = useCallback(async (append = false) => {
    setHistoryLoading(true)
    setHistoryError('')
    try {
      const cursor = append ? historyCursorRef.current : null
      const query = new URLSearchParams({ limit: '20' })
      if (cursor) query.set('cursor', cursor)
      const page = await api.get<{ items: Summary[]; next_cursor: string | null }>(`/conversations?${query}`)
      setHistory((current) => append ? [...current, ...page.items] : page.items)
      historyCursorRef.current = page.next_cursor
      setHistoryCursor(page.next_cursor)
      setHistoryError('')
    } catch (cause) {
      setHistoryError(cause instanceof Error ? cause.message : '无法读取问答历史')
      onError(cause instanceof Error ? cause.message : '无法读取问答历史')
    } finally {
      setHistoryLoading(false)
    }
  }, [onError])

  const refreshPersonalization = useCallback(async () => {
    setPersonalizationLoading(true)
    setPersonalizationError('')
    try {
      const [roleItems, memoryItems, candidateItems] = await Promise.all([
        api.get<AnswerRole[]>('/roles'), api.get<UserMemory[]>('/memory'),
        api.get<MemoryCandidate[]>('/memory/candidates'),
      ])
      setRoles(roleItems)
      setMemories(memoryItems)
      setMemoryCandidates(candidateItems)
      setPersonalizationError('')
    } catch (cause) {
      setPersonalizationError(cause instanceof Error ? cause.message : '无法读取本机问答偏好')
      onError(cause instanceof Error ? cause.message : '无法读取本机问答偏好')
    } finally {
      setPersonalizationLoading(false)
    }
  }, [onError])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void refreshStatus()
      void api.get<Page[]>('/pages').then(setEligiblePages).catch(() => undefined)
      void refreshHistory()
      void refreshPersonalization()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [refreshHistory, refreshPersonalization, refreshStatus])

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
      setRetrievalPurpose(latest?.purpose === 'history' ? 'history' : 'current')
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
    setRetrievalPurpose('current')
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

  async function confirmDelete() {
    if (!pendingDelete) return
    try {
      if (pendingDelete.kind === 'conversation') {
        await api.delete(`/conversations/${pendingDelete.id}`)
        setHistory((current) => current.filter((item) => item.conversation_id !== pendingDelete.id))
        if (conversationId === pendingDelete.id) startNewConversation()
        await refreshHistory()
      } else if (pendingDelete.kind === 'role') {
        await api.delete(`/roles/${pendingDelete.id}`)
        chooseRole('')
        await refreshPersonalization()
      } else {
        await api.delete(`/memory/${pendingDelete.id}`)
        await refreshPersonalization()
      }
      setPendingDelete(null)
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法完成删除')
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

  async function ask(event: FormEvent) {
    event.preventDefault()
    if (!question.trim() || streaming) return
    const controller = new AbortController()
    const approved = approvedQuery.current
    const queryId = typeof approved?.body.request_id === 'string' ? approved.body.request_id : crypto.randomUUID()
    let targetConversation = typeof approved?.body.conversation_id === 'string' ? approved.body.conversation_id : conversationId
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
      const body: Record<string, unknown> = approved?.body ?? {
        question,
        ...(targetConversation ? { conversation_id: targetConversation } : {}),
        fingerprint: settings.embedding_fingerprint,
        purpose: retrievalPurpose,
        answer_mode: answerMode,
        ...(selectedRoleId ? { role_id: selectedRoleId } : {}),
        request_id: queryId,
      }
      if (settings.mode === 'real' && !approved) {
        const preview = await api.post<{ plan: AcceptancePlan; scope: Record<string, unknown> }>('/acceptance-plans', {
          operation: 'model.query', scope: body,
        })
        setPendingQuery({ ...preview, body })
        setQueryState('idle')
        setNotice('请先检查将发送的问题、历史、角色/记忆上下文和页面版本，再独立确认。')
        return
      }
      if (approved) body.acceptance_plan_id = approved.planId
      approvedQuery.current = null
      const response = await fetch('/api/v1/queries', {
        method: 'POST',
        headers: sessionHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!response.ok) {
        const failure = await response.json().catch(() => null) as { error?: { message?: string } } | null
        setQueryState('error')
        setNotice(failure?.error?.message ?? '问题未被接受；请检查输入后重试。')
        return
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

  async function confirmQueryPlan() {
    if (!pendingQuery) return
    try {
      await api.post('/acceptance-plans/' + pendingQuery.plan.plan_id + '/confirm', { scope_sha256: pendingQuery.plan.scope_sha256, scope: pendingQuery.scope })
      approvedQuery.current = { planId: pendingQuery.plan.plan_id, body: pendingQuery.body }
      setPendingQuery(null)
      setNotice('已确认；现在只运行刚才审阅的查询快照。')
      queryForm.current?.requestSubmit()
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : '确认失败；尚未发送查询。')
    }
  }

  async function cancelQueryPlan() {
    if (!pendingQuery) return
    try {
      await api.delete('/acceptance-plans/' + pendingQuery.plan.plan_id)
      setPendingQuery(null)
      setNotice('本次查询计划已取消，没有发送问题或上下文。')
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : '无法撤销本次查询计划。')
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
  const markdownPages = eligiblePages.map((page) => ({ page_id: page.page_id, content_sha256: page.content_sha256, title: String(page.metadata.title ?? ''), relative_path: page.relative_path }))

  return (
    <section className="content-wrap ask-view">
      <div className="page-heading">
        <div><div className="eyebrow">仅使用已确认知识</div><h1>知识问答</h1><p className="lede">每条依据都会回到回答当时的页面版本复核。没有资料时会明确说明。</p></div>
        <button className="button secondary" onClick={startNewConversation}>新建对话</button>
      </div>
      <form ref={queryForm} className="query-form" onSubmit={ask}>
        <label htmlFor="knowledge-question">你的问题</label>
        <div className="query-input-wrap">
          <textarea id="knowledge-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：这个项目已经确认的地点和联系人有哪些？" rows={3} />
          {streaming ? <button type="button" className="button secondary" onClick={cancel}>停止回答</button> : <button className="button primary" disabled={!question.trim()}>开始检索</button>}
        </div>
        <small>回答与历史仅保存在本机；不会自动写入知识页。</small>
        <details className="query-options">
          <summary>资料范围与回答方式</summary>
          <label htmlFor="retrieval-purpose">资料范围</label>
          <select id="retrieval-purpose" value={retrievalPurpose} onChange={(event) => setRetrievalPurpose(event.target.value as RetrievalPurpose)}>
            <option value="current">当前有效资料</option><option value="history">包含历史版本</option>
          </select>
          {retrievalPurpose === 'history' && <p role="note" className="stale-citation-note">历史资料范围会包含已被替代或失效的版本，只供历史参考，不能代表当前规则。</p>}
          <label htmlFor="answer-mode">回答方式</label>
          <select id="answer-mode" value={answerMode} onChange={(event) => setAnswerMode(event.target.value as AnswerMode)}>
            <option value="fact">查找事实</option><option value="comparison">跨材料比较</option><option value="plan">提出工作方案</option>
          </select>
          <label htmlFor="query-role">本次使用角色</label>
          <select id="query-role" value={selectedRoleId} onChange={(event) => chooseRole(event.target.value)}>
            <option value="">不使用角色</option>{roles.map((role) => <option key={role.role_id} value={role.role_id}>{role.name}</option>)}
          </select>
        </details>
      </form>
      <details className="ask-secondary" aria-label="本机问答历史">
        <summary>本机历史</summary>
        <section className="conversation-history">
        <div className="section-title-row"><h2>本机历史</h2><span>只保存在此 profile 和工作库</span></div>
        {historyLoading && history.length === 0 ? <p className="empty-state" role="status">正在读取问答历史…</p> : historyError && history.length === 0 ? <p className="empty-state" role="alert">问答历史读取失败：{historyError}。尚未获得可显示的数据。</p> : history.length === 0 ? <p className="empty-state">还没有问答历史。</p> : <>{historyError && <p role="status">问答历史更新失败：{historyError}；保留上次成功读取的内容。</p>}<ul>
          {history.map((item) => <li key={item.conversation_id} className={item.conversation_id === conversationId ? 'selected' : ''}>
            <button className="history-open" onClick={() => void openConversation(item.conversation_id)}>
              <strong>{item.title}</strong><small>{new Date(item.updated_at).toLocaleString()} · {item.message_count} 个问题 · {stateLabel[item.state]}</small>
            </button>
            <button className="text-button" aria-label={`删除 ${item.title}`} onClick={() => setPendingDelete({ kind: 'conversation', id: item.conversation_id, label: item.title })}>删除</button>
          </li>)}
        </ul></>}
        {historyLoading && history.length > 0 && <p role="status">正在更新问答历史…</p>}
        {historyCursor && <button className="text-button" disabled={historyLoading} onClick={() => void refreshHistory(true)}>加载更早历史</button>}
        </section>
      </details>
      <details className="ask-secondary ask-index">
        <summary>本机索引与更新</summary>
        <section className="index-status-panel">
        <div className="index-status-copy">
          <span className={status?.state === 'ready' ? 'index-state ready' : 'index-state'}>{status?.state === 'stale' ? '本机索引有待更新' : status?.fingerprint ? '本机索引已就绪' : '还没有本机索引'}</span>
          <p>{status?.state === 'stale' ? `${status.stale_pages} 个页面版本尚未进入索引；旧版本不会作为当前依据。` : status?.fingerprint ? status.pages + ' 个页面 · ' + status.chunks + ' 个分块' : '建立或更新索引需要先检查范围，再单独确认。'}</p>
        </div>
        <div className="index-actions"><button className="button secondary" onClick={onOpenApproval}>前往审批查看索引</button></div>
        </section>
        <p className="muted">索引范围预览、真实服务授权和执行记录都在审批页的「索引」类别中处理。</p>
      </details>

      <details className="ask-secondary" aria-label="本机问答偏好与记忆">
        <summary>问答角色与记忆</summary>
        <section className="conversation-history">
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
        <div className="button-row"><button className="button secondary" onClick={() => void saveRole()} disabled={!roleName.trim()}>保存角色</button>{selectedRoleId && <button className="text-button" onClick={() => setPendingDelete({ kind: 'role', id: selectedRoleId, label: roleName || '当前角色' })}>删除角色</button>}</div>
        <h3>待确认记忆</h3>
        {personalizationLoading && roles.length + memories.length + memoryCandidates.length === 0 ? <p role="status" className="empty-state">正在读取问答偏好与记忆…</p> : personalizationError && roles.length + memories.length + memoryCandidates.length === 0 ? <p role="alert" className="empty-state">问答偏好与记忆读取失败：{personalizationError}。尚未获得可显示的数据。</p> : <>{personalizationError && <p role="status">偏好与记忆更新失败：{personalizationError}；保留上次成功读取的内容。</p>}{personalizationLoading && <p role="status">正在更新问答偏好与记忆…</p>}{memoryCandidates.length === 0 ? <p className="empty-state">没有待确认记忆。</p> : memoryCandidates.map((candidate) => <div key={candidate.candidate_id} className="memory-item">
          <textarea aria-label="编辑记忆候选" value={candidateDrafts[candidate.candidate_id] ?? candidate.text} onChange={(event) => setCandidateDrafts((current) => ({ ...current, [candidate.candidate_id]: event.target.value }))} />
          <small>来自本机历史中的本人问题；确认后才会用于回答。</small>
          <button className="button secondary" onClick={() => void confirmMemory(candidate)}>确认并保存</button>
        </div>)}
        <h3>已确认记忆</h3>
        {memories.length === 0 ? <p className="empty-state">目前没有已确认记忆。</p> : memories.map((memory) => <div key={memory.memory_id} className="memory-item">
          <textarea aria-label="编辑已确认记忆" value={memoryDrafts[memory.memory_id] ?? memory.text} onChange={(event) => setMemoryDrafts((current) => ({ ...current, [memory.memory_id]: event.target.value }))} />
          <small>来源于已确认的本人问题</small>
          <div className="button-row"><button className="text-button" onClick={() => void api.patch(`/memory/${memory.memory_id}`, { text: memoryDrafts[memory.memory_id] ?? memory.text }).then(refreshPersonalization).catch((cause: unknown) => onError(cause instanceof Error ? cause.message : '记忆没有保存修改'))}>保存修改</button><button className="text-button" onClick={() => setPendingDelete({ kind: 'memory', id: memory.memory_id, label: '这条已确认记忆' })}>删除记忆</button></div>
        </div>)}</>}
        </section>
      </details>

      {renderedMessages.length > 0 && <section className="conversation-thread" aria-label="对话内容">
        <h2>{thread?.title}</h2>
        {renderedMessages.map((message) => <article className="conversation-turn" key={message.request_id}>
          <div className="user-question"><strong>你</strong><p>{message.question}</p></div>
          <div className="assistant-answer"><strong>回答 · {answerModeLabel[message.answer_mode]} · {stateLabel[message.state]}</strong><StreamingMarkdown className="answer-text" content={message.answer || (message.state === 'running' ? '正在检索与整理…' : '尚无回答内容')} complete={message.state === 'completed'} pageIndex={markdownPages} onOpenPage={onOpenPage} />
            <AnswerDetails details={message} />
            <label className="memory-attestation"><input type="checkbox" checked={memoryAttestations[message.request_id] ?? false} onChange={(event) => setMemoryAttestations((current) => ({ ...current, [message.request_id]: event.target.checked }))} />这是我本人表达的偏好或事实，不是我粘贴、转述的材料或引用</label>
            <button className="text-button" disabled={!memoryAttestations[message.request_id]} onClick={() => void proposeMemory(message)}>创建待确认记忆候选</button>
            {message.error && <p role="status" className="form-error">{message.error}</p>}
            {(message.citations?.length ?? 0) > 0 && <CitationList citations={message.citations ?? []} onOpen={openCitation} />}
          </div>
        </article>)}
      </section>}

      {pendingQuery && <section className="plan-card approval-preview" aria-label="真实问答发送预览">
        <div><strong>请确认本次问答发送范围</strong><span>最多 3 次 HTTP 请求：embedding、rerank、回答各一次；这是调用次数上限，不是金额上限。生成上限 {String(pendingQuery.scope.max_output_tokens)} token，思考预算 {String(pendingQuery.scope.reasoning_effort)}。</span></div>
        <p><strong>问题</strong><br />{String(pendingQuery.scope.question ?? '')}</p>
        <p><strong>资料范围</strong><br />{pendingQuery.scope.purpose === 'history' ? '包含历史版本（仅供历史参考）' : '当前有效资料'}</p>
        <p><strong>将检索的合格页面</strong></p>
        <ul>{Object.keys((pendingQuery.scope.source_versions ?? {}) as Record<string, unknown>).map((id) => <li key={id}>{String(eligiblePages.find((page) => page.page_id === id)?.metadata.title ?? '未命名页面')}</li>)}</ul>
        {(() => { const context = (pendingQuery.scope.context ?? {}) as Record<string, unknown>; const prior = context.previous_user_questions as string[] | undefined; const memories = context.user_memories as string[] | undefined; return <>
          <p><strong>角色</strong><br />{String(context.role_name || '不使用角色')}{context.role_instructions ? `：${String(context.role_instructions)}` : ''}</p>
          <p><strong>已确认记忆</strong></p>{memories?.length ? <ul>{memories.map((memory, index) => <li key={index}>{memory}</li>)}</ul> : <p>无</p>}
          <p><strong>历史问题</strong></p>{prior?.length ? <ul>{prior.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>无</p>}
        </> })()}
        <div className="button-row"><button className="button primary" onClick={() => void confirmQueryPlan()}>确认并发送本次问题</button><button className="button secondary" onClick={() => void cancelQueryPlan()}>取消，不发送</button></div>
      </section>}
      {(answer || citations.length > 0 || queryState !== 'idle') && (!thread?.messages.some((message) => message.request_id === requestId) || streaming) && <section className="answer-panel">
        <div className="answer-heading"><span className="answer-mark">答</span><div><h2>本次回答 · <span role="status">{stateLabel[queryState]}</span></h2><span>{streaming ? '正在读取当前页面…' : citations.length ? '根据已确认资料' : '没有找到可引用的依据'}</span></div></div>
        <StreamingMarkdown className="answer-text" content={answer} complete={!streaming} pageIndex={markdownPages} onOpenPage={onOpenPage} />
        {answerDetails && <AnswerDetails details={answerDetails} />}
        {notice && <p role="status" className={queryState === 'error' ? 'form-error' : 'stale-citation-note'}>{notice}</p>}
        {citations.length > 0 && <CitationList citations={citations} onOpen={openCitation} />}
      </section>}
      {pendingDelete && <ConfirmDialog
        title={pendingDelete.kind === 'conversation' ? '删除这段问答历史？' : pendingDelete.kind === 'role' ? '删除这个问答角色？' : '删除这条已确认记忆？'}
        description={pendingDelete.kind === 'conversation' ? `“${pendingDelete.label}”及其本机对话内容将被删除。` : pendingDelete.kind === 'role' ? `“${pendingDelete.label}”将从本机问答偏好中删除。` : '这条记忆将从本机偏好中删除。'}
        consequence="删除前不会写入任何内容，取消可保留现状。"
        confirmLabel="确认删除" busyLabel="正在删除…" danger
        onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete}
      />}
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
      <span><strong>{citation.heading || '页面内容'}</strong><small>{citation.excerpt}</small><small>{citationStatus(citation)}</small></span>
      <span aria-hidden="true">↗</span>
    </button>)}
  </div>
}

function citationStatus(citation: Citation): string {
  const availability = citation.availability === 'updated'
    ? '原引用版本已更新'
    : citation.availability === 'unavailable'
      ? '原引用已不可用'
      : ''
  const validity = citation.validity === 'superseded'
    ? '已被替代的历史版本，仅限历史参考'
    : citation.validity === 'invalid'
      ? '已失效版本，仅限历史参考'
      : '引用版本仍可用'
  return [availability, validity].filter(Boolean).join(' · ')
}
